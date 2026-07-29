"""Start an Agent Platform Batch Inference job for an explicitly named model."""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LOCATION = re.compile(r"^[a-z]+(?:-[a-z]+)*[0-9]+$")
_RESOURCE_ID = re.compile(r"^[0-9]+$")
_DISPLAY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,127}$")
_BIGQUERY_TABLE = re.compile(
    r"^bq://[a-z][a-z0-9-]{4,28}[a-z0-9]\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$"
)
_BIGQUERY_DATASET = re.compile(r"^bq://[a-z][a-z0-9-]{4,28}[a-z0-9]\.[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class BatchPredictionRequest:
    project_id: str
    location: str
    model_name: str
    input_bigquery_table: str
    output_bigquery_dataset: str
    display_name: str
    machine_type: str


def build_request(
    project_id: str,
    location: str,
    model_name: str,
    input_bigquery_table: str,
    output_bigquery_dataset: str,
    display_name: str,
    machine_type: str,
) -> BatchPredictionRequest:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    if not _LOCATION.fullmatch(location):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    expected = f"projects/{project_id}/locations/{location}/models/"
    if not model_name.startswith(expected) or not _RESOURCE_ID.fullmatch(
        model_name.removeprefix(expected)
    ):
        raise ValueError("model name must be a Model resource in the supplied project and location")
    if not _BIGQUERY_TABLE.fullmatch(input_bigquery_table):
        raise ValueError("input table must use bq://PROJECT.DATASET.TABLE")
    if not _BIGQUERY_DATASET.fullmatch(output_bigquery_dataset):
        raise ValueError("output dataset must use bq://PROJECT.DATASET")
    if not _DISPLAY_NAME.fullmatch(display_name):
        raise ValueError(
            "display name must be 1-128 letters, numbers, spaces, underscores, or hyphens"
        )
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", machine_type):
        raise ValueError("machine type must be a valid Compute Engine machine type")
    return BatchPredictionRequest(
        project_id,
        location,
        model_name,
        input_bigquery_table,
        output_bigquery_dataset,
        display_name,
        machine_type,
    )


class _BatchPredictionClient:
    def __init__(self) -> None:
        from google.cloud import aiplatform

        self._aiplatform = aiplatform

    def start(self, request: BatchPredictionRequest) -> str:
        self._aiplatform.init(project=request.project_id, location=request.location)
        job = self._aiplatform.Model(request.model_name).batch_predict(
            job_display_name=request.display_name,
            bigquery_source=request.input_bigquery_table,
            bigquery_destination_prefix=request.output_bigquery_dataset,
            machine_type=request.machine_type,
            sync=False,
        )
        return str(job.resource_name)


def execute_request(
    request: BatchPredictionRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _BatchPredictionClient,
) -> str:
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return request.model_name
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    job_name = str(client_factory().start(request))
    print(f"started batch prediction job: {job_name}")
    return job_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--input-bigquery-table", required=True)
    parser.add_argument("--output-bigquery-dataset", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--machine-type", default="n1-standard-4")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-billable", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        request = build_request(
            args.project_id,
            args.location,
            args.model_name,
            args.input_bigquery_table,
            args.output_bigquery_dataset,
            args.display_name,
            args.machine_type,
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
