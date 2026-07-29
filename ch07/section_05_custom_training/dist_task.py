"""`CLUSTER_SPEC` に基づくファイル分担のための小さな補助関数。"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

from task import DEFAULT_DATA_PATH, FileSystem, _filesystem, gcs_uri, train


@dataclass(frozen=True)
class WorkerAssignment:
    rank: int
    world_size: int
    task_type: str
    task_index: int


def assignment_from_cluster_spec(raw: str | None) -> WorkerAssignment:
    """Agent Platformの`CLUSTER_SPEC`を検証し、決定的なrankを返す。"""
    if not raw:
        return WorkerAssignment(rank=0, world_size=1, task_type="chief", task_index=0)
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("CLUSTER_SPEC は有効な JSON である必要があります") from exc
    cluster, task = spec.get("cluster"), spec.get("task")
    if not isinstance(cluster, dict) or not isinstance(task, dict):
        raise ValueError("CLUSTER_SPEC には cluster と task オブジェクトが必要です")
    task_type, task_index = task.get("type"), task.get("index")
    if not isinstance(task_type, str) or not isinstance(task_index, int) or task_index < 0:
        raise ValueError("CLUSTER_SPEC.task.type と 0 以上の task.index が必要です")
    workers: list[tuple[str, int]] = []
    for pool_name in sorted(cluster):
        endpoints = cluster[pool_name]
        if not isinstance(pool_name, str) or not isinstance(endpoints, list):
            raise ValueError("CLUSTER_SPEC.cluster は worker pool ごとの配列にしてください")
        workers.extend((pool_name, index) for index in range(len(endpoints)))
    if not workers or (task_type, task_index) not in workers:
        raise ValueError("CLUSTER_SPEC.task が cluster 内の worker を参照していません")
    return WorkerAssignment(
        workers.index((task_type, task_index)), len(workers), task_type, task_index
    )


def shard_files(files: list[str], assignment: WorkerAssignment) -> list[str]:
    """ソート済み URI を rank ごとに重複なく分ける。"""
    return sorted(files)[assignment.rank :: assignment.world_size]


def run_distributed(
    args: argparse.Namespace,
    *,
    cluster_spec: str | None = None,
    filesystem: FileSystem | None = None,
) -> str:
    """Shard CSV objects per worker and train one independently saved model."""
    assignment = assignment_from_cluster_spec(
        cluster_spec if cluster_spec is not None else os.environ.get("CLUSTER_SPEC")
    )
    model_path = (
        f"{args.model_dir}/{assignment.task_type}-{assignment.task_index}/lgbm_model.joblib"
    )
    if args.dry_run:
        print(
            "DRY RUN: "
            f"rank={assignment.rank}/{assignment.world_size}; "
            f"data={gcs_uri(args.bucket_name, args.data_path)}; "
            f"model={gcs_uri(args.bucket_name, model_path)}"
        )
        return gcs_uri(args.bucket_name, model_path)
    fs = filesystem or _filesystem()
    files = sorted(fs.glob(gcs_uri(args.bucket_name, args.data_path)))
    assigned = shard_files(files, assignment)
    if not assigned:
        raise FileNotFoundError(f"rank {assignment.rank} に割り当てる CSV がありません")
    train_args = argparse.Namespace(
        bucket_name=args.bucket_name,
        data_path=args.data_path,
        model_path=model_path,
        dry_run=False,
    )
    return train(train_args, filesystem=fs, assigned_files=assigned)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYC Taxi worker-sharded LightGBM trainer")
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--model-dir", default="models/nyc-taxi-tip-distributed")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    run_distributed(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
