from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "section_02_dataset_preparation"
sys.path.insert(0, str(SCRIPTS))

import data_prepare  # noqa: E402

IMAGE_SCRIPTS = Path(__file__).parents[1] / "section_08_advanced_image"
sys.path.insert(0, str(IMAGE_SCRIPTS))
import data_flowers_manifest  # noqa: E402


class DataPrepareTests(unittest.TestCase):
    def test_render_create_replaces_project_placeholder(self) -> None:
        rendered = data_prepare.render_template(
            "create", "example-project-123", "gcds_ch07_validation", "training_table"
        )
        self.assertIn("`example-project-123.gcds_ch07_validation.training_table`", rendered)
        self.assertIn("TABLESAMPLE SYSTEM (10 PERCENT)", rendered)
        self.assertNotIn("{{", rendered)

    def test_export_requires_bucket(self) -> None:
        with self.assertRaisesRegex(ValueError, "bucket-name"):
            data_prepare.render_template(
                "export", "example-project-123", "gcds_ch07_validation", "training_table"
            )

    def test_rejects_unsafe_dataset_or_table_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset ID"):
            data_prepare.render_template(
                "create", "example-project-123", "shared.dataset", "training_table"
            )
        with self.assertRaisesRegex(ValueError, "table ID"):
            data_prepare.render_template(
                "create", "example-project-123", "gcds_ch07_validation", "table-name"
            )

    def test_cli_rejects_invalid_project_without_cloud_call(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = data_prepare.main(
                [
                    "render",
                    "create",
                    "--project-id",
                    "INVALID",
                    "--dataset-id",
                    "gcds_ch07_validation",
                    "--table-id",
                    "training_table",
                ]
            )
        self.assertEqual(exit_code, 2)
        self.assertIn("project ID", stderr.getvalue())


class FlowerManifestTests(unittest.TestCase):
    def _source_tree(self, root: Path) -> Path:
        source = root / "flower_photos"
        for label in ("daisy", "dandelion", "roses", "sunflowers", "tulips"):
            directory = source / label
            directory.mkdir(parents=True)
            (directory / f"{label}.jpg").write_bytes(b"not-an-image")
        return source

    def test_manifest_is_sorted_and_uses_expected_gcs_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self._source_tree(Path(temporary))
            lines = data_flowers_manifest.build_manifest(source, "example-nyc-taxi-bucket")
        self.assertEqual(len(lines), 5)
        self.assertEqual(
            lines[0],
            "gs://example-nyc-taxi-bucket/data/flowers_photos/daisy/daisy.jpg,daisy",
        )

    def test_dry_run_does_not_write_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._source_tree(root)
            output = root / "flowers_import.csv"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = data_flowers_manifest.main(
                    [
                        "--source-dir",
                        str(source),
                        "--bucket-name",
                        "example-nyc-taxi-bucket",
                        "--output",
                        str(output),
                        "--dry-run",
                    ]
                )
        self.assertEqual(exit_code, 0)
        self.assertFalse(output.exists())
        self.assertIn("dry-run", stdout.getvalue())

    def test_cli_writes_expected_manifest_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._source_tree(root)
            output = root / "flowers_import.csv"
            exit_code = data_flowers_manifest.main(
                [
                    "--source-dir",
                    str(source),
                    "--bucket-name",
                    "example-flowers-bucket",
                    "--output",
                    str(output),
                ]
            )
            rows = output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(rows), 5)
        self.assertEqual(
            rows[0],
            "gs://example-flowers-bucket/data/flowers_photos/daisy/daisy.jpg,daisy",
        )

    def test_readme_manifest_arguments_exist_in_cli(self) -> None:
        args = data_flowers_manifest.build_parser().parse_args(
            [
                "--source-dir",
                "flower_photos",
                "--bucket-name",
                "example-flowers-bucket",
                "--output",
                "flowers_import.csv",
                "--dry-run",
            ]
        )
        self.assertEqual(args.source_dir, Path("flower_photos"))
        self.assertEqual(args.output, Path("flowers_import.csv"))
        self.assertTrue(args.dry_run)
