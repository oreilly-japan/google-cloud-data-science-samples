"""Custom Training / HPT のリクエストを組み立てる安全な CLI。

``--dry-run`` 指定時は、認証、Google Cloudクライアント生成、ネットワーク通信を
行わない。``--render-hpt-config``はローカルにYAMLを生成するだけで通信しない。
Cloudへ送信する非dry-run実行は、``--allow-billable``を明示した場合だけ許可する。
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

_RESOURCE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


@dataclass(frozen=True)
class TrainingRequest:
    mode: str
    project_id: str
    region: str
    display_name: str
    bucket_name: str
    image_uri: str
    machine_type: str
    workers: int
    package_path: str = "."
    max_trial_count: int | None = None
    parallel_trial_count: int | None = None
    hpt_config_path: str | None = None


def _required(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"{name} を指定してください")
    return value


def _safe_name(value: str, name: str) -> str:
    if not _RESOURCE.fullmatch(value):
        raise ValueError(f"{name} は小文字、数字、ハイフンで始まる 1〜63 文字にしてください")
    return value


def _bucket_name(value: str) -> str:
    if value.startswith("gs://") or "/" in value or len(value) < 3 or len(value) > 63:
        raise ValueError("bucket-name は gs:// を除く 3〜63 文字のバケット名にしてください")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*[a-z0-9]", value):
        raise ValueError("bucket-name には小文字、数字、ドット、ハイフンだけを使用してください")
    return value


def build_request(args: argparse.Namespace) -> TrainingRequest:
    mode = _required(args.mode, "--mode")
    if mode not in {"cpu", "distributed", "gpu", "hpt"}:
        raise ValueError("--mode は cpu, distributed, gpu, hpt のいずれかです")
    workers = args.workers if mode == "distributed" else 1
    if workers < 2 and mode == "distributed":
        raise ValueError("distributed mode の --workers は 2 以上にしてください")
    if args.workers < 1:
        raise ValueError("--workers は 1 以上にしてください")
    max_trials = args.max_trial_count if mode == "hpt" else None
    parallel_trials = args.parallel_trial_count if mode == "hpt" else None
    if mode == "hpt":
        if (
            max_trials is None
            or parallel_trials is None
            or max_trials < 1
            or parallel_trials < 1
            or parallel_trials > max_trials
        ):
            raise ValueError("HPT は 1 <= --parallel-trial-count <= --max-trial-count が必要です")
    hpt_config_path = args.hpt_config_path if mode == "hpt" else None
    if mode == "hpt" and not hpt_config_path and not args.render_hpt_config:
        raise ValueError("HPT には --hpt-config-path を指定してください")
    return TrainingRequest(
        mode=mode,
        project_id=_safe_name(_required(args.project_id, "--project-id"), "project-id"),
        region=_safe_name(_required(args.region, "--region"), "region"),
        display_name=_safe_name(_required(args.display_name, "--display-name"), "display-name"),
        bucket_name=_bucket_name(_required(args.bucket_name, "--bucket-name")),
        image_uri=_required(args.image_uri, "--image-uri"),
        machine_type=_required(args.machine_type, "--machine-type"),
        workers=workers,
        package_path=args.package_path,
        max_trial_count=max_trials,
        parallel_trial_count=parallel_trials,
        hpt_config_path=hpt_config_path,
    )


def command_for(request: TrainingRequest) -> list[str]:
    """gcloud コマンドを値の展開なしの配列として返す。まだ実行はしない。"""
    base = ["gcloud", "ai"]
    if request.mode == "hpt":
        return base + [
            "hp-tuning-jobs",
            "create",
            f"--project={request.project_id}",
            f"--region={request.region}",
            f"--display-name={request.display_name}",
            f"--config={request.hpt_config_path}",
            f"--max-trial-count={request.max_trial_count}",
            f"--parallel-trial-count={request.parallel_trial_count}",
        ]
    if request.mode == "gpu":
        spec = (
            f"machine-type={request.machine_type},replica-count=1,container-image-uri={request.image_uri},"
            "accelerator=type=nvidia-tesla-t4,count=1"
        )
    else:
        module = "task" if request.mode == "cpu" else "dist_task"
        spec = (
            f"machine-type={request.machine_type},replica-count=1,executor-image-uri={request.image_uri},"
            f"local-package-path={request.package_path},python-module={module}"
        )
    command = base + [
        "custom-jobs",
        "create",
        f"--project={request.project_id}",
        f"--region={request.region}",
        f"--display-name={request.display_name}",
    ]
    command.append(f"--worker-pool-spec={spec}")
    if request.mode == "distributed":
        # Automatic packaging fields belong only to the first worker pool.
        # Later pools reuse that training application.
        secondary_spec = f"machine-type={request.machine_type},replica-count=1"
        command.extend(f"--worker-pool-spec={secondary_spec}" for _ in range(request.workers - 1))
    command.append(f"--args=--bucket-name={request.bucket_name}")
    return command


def render_hpt_config(request: TrainingRequest, template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    values = {
        "__MACHINE_TYPE__": request.machine_type,
        "__IMAGE_URI__": request.image_uri,
        "__BUCKET_NAME__": request.bucket_name,
    }
    for marker, value in values.items():
        template = template.replace(marker, value)
    if "__" in template:
        raise ValueError("HPT テンプレートに未置換の値があります")
    return template


def execute_request(
    request: TrainingRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    runner: Callable[[Sequence[str]], object] | None = None,
) -> list[str]:
    """リクエストを実行する。runner 注入により実クラウドなしで検証できる。"""
    command = command_for(request)
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", " ".join(command))
        return command
    if not allow_billable:
        raise PermissionError("非 dry-run は --allow-billable を明示してください")
    (runner or (lambda argv: subprocess.run(argv, check=True)))(command)
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Custom Training のリクエスト作成・送信")
    parser.add_argument("--mode", required=True, choices=("cpu", "distributed", "hpt", "gpu"))
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument(
        "--image-uri",
        required=True,
        help="検証済みの事前ビルドまたは Artifact Registry イメージ URI",
    )
    parser.add_argument("--machine-type", default="n1-standard-4")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--package-path",
        default=".",
        help="directory containing task.py/dist_task.py and requirements.txt",
    )
    parser.add_argument("--max-trial-count", type=int, default=20)
    parser.add_argument("--parallel-trial-count", type=int, default=4)
    parser.add_argument(
        "--hpt-config-path", help="render_hpt_config で生成・確認した HPT YAML のパス"
    )
    parser.add_argument(
        "--render-hpt-config",
        metavar="PATH",
        help="HPT YAML を PATH に生成して終了（Cloud API は呼ばない）",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="API/認証/ネットワークなしでコマンドを表示"
    )
    parser.add_argument(
        "--allow-billable", action="store_true", help="課金可能な gcloud 実行を明示的に許可"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        request = build_request(args)
        if args.render_hpt_config:
            if request.mode != "hpt":
                raise ValueError("--render-hpt-config は --mode hpt と組み合わせてください")
            output = Path(args.render_hpt_config)
            output.write_text(
                render_hpt_config(request, Path(__file__).with_name("hptuning_config.yaml")),
                encoding="utf-8",
            )
            print(f"HPT 設定を書き出しました: {output}")
            return 0
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (ValueError, PermissionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
