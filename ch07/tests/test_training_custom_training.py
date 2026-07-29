from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

CUSTOM = Path(__file__).resolve().parents[1] / "section_05_custom_training"
sys.path.insert(0, str(CUSTOM))

import dist_task  # noqa: E402
import hpt_task  # noqa: E402
import submit_custom_training as submit  # noqa: E402
import task  # noqa: E402


def load_gpu_module():
    spec = importlib.util.spec_from_file_location("gpu_dl_task", CUSTOM / "gpu" / "dl_task.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cpu_args(**overrides):
    values = dict(
        mode="cpu",
        project_id="example-project",
        region="us-central1",
        display_name="cpu-run",
        bucket_name="example.bucket",
        image_uri="example/image:tag",
        machine_type="n1-standard-4",
        workers=2,
        package_path=".",
        max_trial_count=20,
        parallel_trial_count=4,
        hpt_config_path=None,
        render_hpt_config=None,
    )
    values.update(overrides)
    return Namespace(**values)


def test_cpu_trainer_dry_run_does_not_create_filesystem(capsys):
    args = task.build_parser().parse_args(["--bucket-name", "example.bucket", "--dry-run"])
    assert task.train(args) == "gs://example.bucket/models/nyc-taxi-tip/lgbm_model.joblib"
    assert "DRY RUN" in capsys.readouterr().out


@pytest.mark.parametrize("bucket,path", [("gs://bad", "data/a.csv"), ("good-bucket", "../a.csv")])
def test_cpu_trainer_rejects_unsafe_gcs_values(bucket, path):
    with pytest.raises(ValueError):
        task.gcs_uri(bucket, path)


def test_cluster_spec_assigns_and_shards_deterministically():
    raw = '{"cluster":{"chief":["chief"],"worker":["worker"]},"task":{"type":"worker","index":0}}'
    assignment = dist_task.assignment_from_cluster_spec(raw)
    assert (assignment.rank, assignment.world_size) == (1, 2)
    assert dist_task.shard_files(["a", "b", "c", "d"], assignment) == ["b", "d"]


def test_cluster_spec_rejects_unknown_task():
    with pytest.raises(ValueError, match="参照"):
        dist_task.assignment_from_cluster_spec(
            '{"cluster":{"chief":["x"]},"task":{"type":"worker","index":0}}'
        )


def test_distributed_entrypoint_shards_and_uses_unique_model(monkeypatch):
    raw = '{"cluster":{"chief":["chief"],"worker":["worker"]},"task":{"type":"worker","index":0}}'
    args = dist_task.build_parser().parse_args(["--bucket-name", "example.bucket"])

    class FakeFs:
        def glob(self, _: str):
            return ["a.csv", "b.csv", "c.csv", "d.csv"]

        def open(self, path, mode):
            raise AssertionError((path, mode))

    captured = {}

    def fake_train(train_args, filesystem=None, assigned_files=None):
        captured["model_path"] = train_args.model_path
        captured["files"] = assigned_files
        return f"gs://example.bucket/{train_args.model_path}"

    monkeypatch.setattr(dist_task, "train", fake_train)
    result = dist_task.run_distributed(args, cluster_spec=raw, filesystem=FakeFs())
    assert captured["files"] == ["b.csv", "d.csv"]
    assert captured["model_path"].endswith("worker-0/lgbm_model.joblib")
    assert result.endswith("worker-0/lgbm_model.joblib")


def test_hpt_reporter_is_injectable_and_validates_value():
    calls = []
    hpt_task.report_rmse(1.25, lambda metric, value, step: calls.append((metric, value, step)))
    assert calls == [("rmse", 1.25, 1)]
    with pytest.raises(ValueError):
        hpt_task.report_rmse(float("nan"), lambda *_: None)


def test_hpt_trainer_dry_run_needs_no_filesystem_or_reporter(capsys):
    args = hpt_task.build_parser().parse_args(["--bucket-name", "example.bucket", "--dry-run"])
    assert hpt_task.train(args) is None
    assert "DRY RUN" in capsys.readouterr().out


def test_hpt_accepts_parameter_id_argument_names():
    args = hpt_task.build_parser().parse_args(
        [
            "--bucket-name",
            "example.bucket",
            "--learning_rate",
            "0.02",
            "--num_leaves",
            "64",
            "--dry-run",
        ]
    )
    assert args.learning_rate == 0.02
    assert args.num_leaves == 64


def test_request_dry_run_has_no_runner_call():
    request = submit.build_request(cpu_args())
    command = submit.execute_request(
        request, dry_run=True, allow_billable=False, runner=lambda _: pytest.fail("called")
    )
    assert command[:3] == ["gcloud", "ai", "custom-jobs"]
    assert any("python-module=task" in value for value in command)


def test_request_requires_explicit_billing_and_injects_runner():
    request = submit.build_request(cpu_args())
    with pytest.raises(PermissionError):
        submit.execute_request(request, dry_run=False, allow_billable=False)
    calls = []
    submit.execute_request(
        request, dry_run=False, allow_billable=True, runner=lambda command: calls.append(command)
    )
    assert len(calls) == 1


def test_distributed_gpu_and_hpt_request_shapes(tmp_path):
    distributed = submit.build_request(
        cpu_args(mode="distributed", workers=2, display_name="dist-run")
    )
    assert (
        sum(value.startswith("--worker-pool-spec=") for value in submit.command_for(distributed))
        == 2
    )
    distributed_specs = [
        value
        for value in submit.command_for(distributed)
        if value.startswith("--worker-pool-spec=")
    ]
    assert "local-package-path=" in distributed_specs[0]
    assert "local-package-path=" not in distributed_specs[1]
    gpu = submit.build_request(cpu_args(mode="gpu", display_name="gpu-run"))
    gpu_command = submit.command_for(gpu)
    assert any(
        "container-image-uri=" in value and "accelerator=type=nvidia-tesla-t4,count=1" in value
        for value in gpu_command
    )
    output = tmp_path / "hpt.yaml"
    hpt = submit.build_request(
        cpu_args(mode="hpt", display_name="hpt-run", hpt_config_path=str(output))
    )
    output.write_text(
        submit.render_hpt_config(hpt, CUSTOM / "hptuning_config.yaml"), encoding="utf-8"
    )
    rendered = output.read_text(encoding="utf-8")
    assert "__MACHINE_TYPE__" not in rendered
    assert "__IMAGE_URI__" not in rendered
    assert "__BUCKET_NAME__" not in rendered
    assert f"--config={output}" in submit.command_for(hpt)
    command = submit.execute_request(
        hpt, dry_run=True, allow_billable=False, runner=lambda _: pytest.fail("called")
    )
    assert f"--config={output}" in command


def test_readme_hpt_arguments_exist_in_cli():
    args = submit.build_parser().parse_args(
        [
            "--mode",
            "hpt",
            "--project-id",
            "example-project-123",
            "--region",
            "us-central1",
            "--display-name",
            "nyc-taxi-hpt",
            "--bucket-name",
            "example-training-bucket",
            "--image-uri",
            "us-central1-docker.pkg.dev/example/project/hpt-trainer:tag",
            "--render-hpt-config",
            "hptuning_config.rendered.yaml",
            "--max-trial-count",
            "20",
            "--parallel-trial-count",
            "4",
            "--dry-run",
            "--allow-billable",
        ]
    )
    assert args.mode == "hpt"
    assert args.render_hpt_config == "hptuning_config.rendered.yaml"
    assert args.max_trial_count == 20
    assert args.parallel_trial_count == 4
    assert args.dry_run
    assert args.allow_billable


def test_request_rejects_invalid_hpt_and_bucket():
    with pytest.raises(ValueError, match="parallel"):
        submit.build_request(
            cpu_args(mode="hpt", hpt_config_path="config.yaml", parallel_trial_count=21)
        )
    with pytest.raises(ValueError, match="bucket-name"):
        submit.build_request(cpu_args(bucket_name="gs://wrong"))


def test_gpu_dry_run_and_invalid_input(capsys):
    gpu = load_gpu_module()
    args = gpu.build_parser().parse_args(["--bucket-name", "example.bucket", "--dry-run"])
    assert gpu.train(args).endswith("/dl_model.pth")
    assert "DRY RUN" in capsys.readouterr().out
    invalid = gpu.build_parser().parse_args(
        ["--bucket-name", "example.bucket", "--epochs", "0", "--dry-run"]
    )
    with pytest.raises(ValueError, match="epochs"):
        gpu.train(invalid)
