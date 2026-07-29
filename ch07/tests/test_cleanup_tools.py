from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).parents[1]
sys.path.insert(0, str(SCRIPTS))

import cleanup_ch07  # noqa: E402


class CleanupTests(unittest.TestCase):
    def test_only_allowlisted_prefixes_are_planned(self) -> None:
        commands = cleanup_ch07.build_cleanup_commands(
            "example-project-123",
            "example-nyc-taxi-bucket",
            ["data/flowers_photos/"],
            "retrain-nyc-taxi-model",
            "us-central1",
        )
        self.assertEqual(commands[0][-1], "gs://example-nyc-taxi-bucket/data/flowers_photos/")
        self.assertEqual(commands[1][4], "retrain-nyc-taxi-model")

    def test_bucket_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "allowed Chapter 7"):
            cleanup_ch07.build_cleanup_commands(
                "example-project-123", "example-nyc-taxi-bucket", [""], None, None
            )

    def test_default_mode_is_dry_run(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cleanup_ch07.main(
                [
                    "--project-id",
                    "example-project-123",
                    "--bucket-name",
                    "example-nyc-taxi-bucket",
                    "--prefix",
                    "data/nyc-taxi-tip-2022/",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertIn("dry-run", stdout.getvalue())

    def test_execute_requires_literal_confirmation_before_runner(self) -> None:
        calls: list[object] = []
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cleanup_ch07.main(
                [
                    "--project-id",
                    "example-project-123",
                    "--bucket-name",
                    "example-nyc-taxi-bucket",
                    "--prefix",
                    "data/nyc-taxi-tip-2022/",
                    "--execute",
                ],
                runner=lambda *args, **kwargs: calls.append((args, kwargs)),
            )
        self.assertEqual(exit_code, 2)
        self.assertEqual(calls, [])
        self.assertIn("requires --confirm", stderr.getvalue())
