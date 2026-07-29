"""Create an Agent Platform tabular Dataset from an explicitly supplied BigQuery table.

The ``--dry-run`` mode validates the arguments and prints the request without
creating credentials or a Google Cloud client.  A non-dry-run needs
``--allow-billable``.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LOCATION = re.compile(r"^[a-z]+(?:-[a-z]+)*[0-9]+$")
_DISPLAY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,127}$")
_BIGQUERY_TABLE = re.compile(
    r"^bq://([a-z][a-z0-9-]{4,28}[a-z0-9])\.([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$"
)
_TABULAR_SCHEMA = "gs://google-cloud-aiplatform/schema/dataset/metadata/tabular_1.0.0.yaml"


def _validate_project_id(value: str) -> str:
    if not _PROJECT_ID.fullmatch(value):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    return value


def _validate_location(value: str) -> str:
    if not _LOCATION.fullmatch(value):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    return value


def _validate_display_name(value: str) -> str:
    if not _DISPLAY_NAME.fullmatch(value):
        raise ValueError(
            "display name must be 1-128 letters, numbers, spaces, underscores, or hyphens"
        )
    return value


def _validate_bigquery_table(value: str) -> str:
    if not _BIGQUERY_TABLE.fullmatch(value):
        raise ValueError("BigQuery table must use bq://PROJECT.DATASET.TABLE")
    return value


@dataclass(frozen=True)
class DatasetRequest:
    project_id: str
    location: str
    display_name: str
    bigquery_source: str

    @property
    def parent(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}"

    def create_dataset_body(self) -> dict[str, str]:
        return {"display_name": self.display_name, "metadata_schema_uri": _TABULAR_SCHEMA}

    def import_config(self) -> dict[str, dict[str, str]]:
        return {"bigquery_source": {"input_uri": self.bigquery_source}}


def build_request(
    project_id: str, location: str, display_name: str, bigquery_source: str
) -> DatasetRequest:
    """Validate CLI values and produce inspectable Dataset API request data."""
    return DatasetRequest(
        project_id=_validate_project_id(project_id),
        location=_validate_location(location),
        display_name=_validate_display_name(display_name),
        bigquery_source=_validate_bigquery_table(bigquery_source),
    )


class _DatasetClient:
    """Small adapter to keep the Google client lazy and replaceable in tests."""

    def __init__(self) -> None:
        from google.cloud import aiplatform_v1

        self._aiplatform_v1 = aiplatform_v1
        self._client = aiplatform_v1.DatasetServiceClient()

    def create_and_import(self, request: DatasetRequest) -> str:
        dataset = self._aiplatform_v1.Dataset(**request.create_dataset_body())
        created = self._client.create_dataset(parent=request.parent, dataset=dataset).result()
        dataset_name = str(created.name)
        import_config = self._aiplatform_v1.ImportDataConfig(**request.import_config())
        self._client.import_data(name=dataset_name, import_configs=[import_config]).result()
        return dataset_name


def execute_request(
    request: DatasetRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _DatasetClient,
) -> str:
    """Create and import only when explicitly allowed; return the dataset resource name."""
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return request.parent
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    dataset_name = str(client_factory().create_and_import(request))
    print(f"created dataset: {dataset_name}")
    return dataset_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--bigquery-source", required=True, metavar="bq://PROJECT.DATASET.TABLE")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-billable", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        request = build_request(
            args.project_id, args.location, args.display_name, args.bigquery_source
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
