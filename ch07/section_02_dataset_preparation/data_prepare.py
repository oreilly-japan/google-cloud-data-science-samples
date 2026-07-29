"""Render and validate the Chapter 7 BigQuery SQL templates without cloud access."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")
_BIGQUERY_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$")
_TEMPLATES = {
    "create": "create_bigquery_table.sql",
    "export": "export_to_gcs.sql",
}


def _validate_project_id(value: str) -> str:
    if not _PROJECT_ID.fullmatch(value):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    return value


def _validate_bucket_name(value: str) -> str:
    if not _BUCKET_NAME.fullmatch(value) or ".." in value:
        raise ValueError("bucket name is not a valid Cloud Storage bucket name")
    return value


def _validate_bigquery_id(value: str, name: str) -> str:
    if not _BIGQUERY_ID.fullmatch(value):
        raise ValueError(f"{name} must use only letters, numbers, or underscores")
    return value


def render_template(
    kind: str,
    project_id: str,
    dataset_id: str,
    table_id: str,
    bucket_name: str | None = None,
) -> str:
    """Return a fully substituted SQL template; this function performs no I/O or API calls."""
    if kind not in _TEMPLATES:
        raise ValueError(f"unknown template: {kind}")
    project_id = _validate_project_id(project_id)
    dataset_id = _validate_bigquery_id(dataset_id, "dataset ID")
    table_id = _validate_bigquery_id(table_id, "table ID")
    if kind == "export" and bucket_name is None:
        raise ValueError("--bucket-name is required for the export template")
    if bucket_name is not None:
        bucket_name = _validate_bucket_name(bucket_name)

    template_path = Path(__file__).with_name(_TEMPLATES[kind])
    rendered = template_path.read_text(encoding="utf-8")
    for marker, value in {
        "{{PROJECT_ID}}": project_id,
        "{{DATASET_ID}}": dataset_id,
        "{{TABLE_ID}}": table_id,
    }.items():
        rendered = rendered.replace(marker, value)
    if bucket_name is not None:
        rendered = rendered.replace("{{BUCKET_NAME}}", bucket_name)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("a required template placeholder was not replaced")
    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    render = subparsers.add_parser(
        "render", help="print substituted SQL; does not call Google Cloud"
    )
    render.add_argument("template", choices=sorted(_TEMPLATES))
    render.add_argument("--project-id", required=True)
    render.add_argument("--dataset-id", required=True)
    render.add_argument("--table-id", required=True)
    render.add_argument("--bucket-name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(
            render_template(
                args.template,
                args.project_id,
                args.dataset_id,
                args.table_id,
                args.bucket_name,
            ),
            end="",
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
