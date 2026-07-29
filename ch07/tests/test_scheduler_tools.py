from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "section_06_scheduler"
sys.path.insert(0, str(SCRIPTS))

import scheduler_validate  # noqa: E402


class SchedulerPayloadTests(unittest.TestCase):
    def test_rendered_payload_is_json_and_has_no_placeholders(self) -> None:
        values = {
            "JOB_DISPLAY_NAME": "nyc-taxi-weekly",
            "IMAGE_URI": "us-docker.pkg.dev/example-project-123/repo/trainer:latest",
            "BUCKET_NAME": "example-nyc-taxi-bucket",
            "RUNTIME_SERVICE_ACCOUNT": ("gcds-runtime@example-project-123.iam.gserviceaccount.com"),
            "RUN_ID": "20260729-ab12",
        }
        payload = scheduler_validate.render_payload(values)
        encoded = json.dumps(payload)
        self.assertNotIn("${", encoded)
        self.assertEqual(payload["displayName"], "nyc-taxi-weekly")
        labels = payload["labels"]
        assert isinstance(labels, dict)
        self.assertEqual(labels["sample-run"], "20260729-ab12")
        job_spec = payload["jobSpec"]
        assert isinstance(job_spec, dict)
        self.assertEqual(
            job_spec["serviceAccount"],
            "gcds-runtime@example-project-123.iam.gserviceaccount.com",
        )
        scheduling = job_spec["scheduling"]
        assert isinstance(scheduling, dict)
        self.assertEqual(scheduling["timeout"], "1800s")
        self.assertFalse(scheduling["restartJobOnWorkerRestart"])
        pools = job_spec["workerPoolSpecs"]
        assert isinstance(pools, list)
        pool = pools[0]
        assert isinstance(pool, dict)
        container = pool["containerSpec"]
        assert isinstance(container, dict)
        self.assertEqual(
            container["args"],
            ["--bucket-name=example-nyc-taxi-bucket"],
        )

    def test_cli_rejects_missing_values(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = scheduler_validate.main(["--set", "BUCKET_NAME=example-nyc-taxi-bucket"])
        self.assertEqual(exit_code, 2)
        self.assertIn("missing values", stderr.getvalue())

    def test_rejects_non_service_account_runtime_identity(self) -> None:
        values = {
            "JOB_DISPLAY_NAME": "nyc-taxi-weekly",
            "IMAGE_URI": "us-docker.pkg.dev/example-project-123/repo/trainer:latest",
            "BUCKET_NAME": "example-nyc-taxi-bucket",
            "RUNTIME_SERVICE_ACCOUNT": "human@example.com",
            "RUN_ID": "20260729-ab12",
        }
        with self.assertRaisesRegex(ValueError, "service account email"):
            scheduler_validate.render_payload(values)

    def test_cli_only_prints_payload(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = scheduler_validate.main(
                [
                    "--set",
                    "JOB_DISPLAY_NAME=nyc-taxi-weekly",
                    "--set",
                    "IMAGE_URI=us-docker.pkg.dev/example-project-123/repo/trainer:latest",
                    "--set",
                    "BUCKET_NAME=example-nyc-taxi-bucket",
                    "--set",
                    (
                        "RUNTIME_SERVICE_ACCOUNT="
                        "gcds-runtime@example-project-123.iam.gserviceaccount.com"
                    ),
                    "--set",
                    "RUN_ID=20260729-ab12",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["displayName"], "nyc-taxi-weekly")
