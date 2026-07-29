"""Start Agent Platform AutoML training from an existing tabular Dataset.

This is a Python SDK counterpart to the Console example in section 7.3.  The
default ``--dry-run`` validates and displays the request without authentication.
"""

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
_COLUMN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _project(value: str) -> str:
    if not _PROJECT_ID.fullmatch(value):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    return value


def _location(value: str) -> str:
    if not _LOCATION.fullmatch(value):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    return value


def _display_name(value: str, field: str) -> str:
    if not _DISPLAY_NAME.fullmatch(value):
        raise ValueError(f"{field} must be 1-128 letters, numbers, spaces, underscores, or hyphens")
    return value


def _dataset_name(value: str, project_id: str, location: str) -> str:
    expected = f"projects/{project_id}/locations/{location}/datasets/"
    if not value.startswith(expected) or not _RESOURCE_ID.fullmatch(value.removeprefix(expected)):
        raise ValueError(
            "dataset name must be a Dataset resource in the supplied project and location"
        )
    return value


@dataclass(frozen=True)
class TabularAutoMLRequest:
    project_id: str
    location: str
    dataset_name: str
    target_column: str
    budget_milli_node_hours: int
    model_display_name: str
    training_job_display_name: str


def build_request(
    project_id: str,
    location: str,
    dataset_name: str,
    target_column: str,
    budget_milli_node_hours: int,
    model_display_name: str,
    training_job_display_name: str,
) -> TabularAutoMLRequest:
    """Return a validated, locally inspectable AutoML request."""
    project_id = _project(project_id)
    location = _location(location)
    if not _COLUMN.fullmatch(target_column):
        raise ValueError("target column must be a BigQuery-compatible column name")
    if budget_milli_node_hours < 1_000:
        raise ValueError("budget must be at least 1000 milli node hours")
    return TabularAutoMLRequest(
        project_id=project_id,
        location=location,
        dataset_name=_dataset_name(dataset_name, project_id, location),
        target_column=target_column,
        budget_milli_node_hours=budget_milli_node_hours,
        model_display_name=_display_name(model_display_name, "model display name"),
        training_job_display_name=_display_name(
            training_job_display_name, "training job display name"
        ),
    )


class _AutoMLClient:
    def __init__(self) -> None:
        from google.cloud import aiplatform

        self._aiplatform = aiplatform

    def start_training(self, request: TabularAutoMLRequest) -> str:
        self._aiplatform.init(project=request.project_id, location=request.location)
        dataset = self._aiplatform.TabularDataset(request.dataset_name)
        job = self._aiplatform.AutoMLTabularTrainingJob(
            display_name=request.training_job_display_name,
            optimization_prediction_type="regression",
            optimization_objective="minimize-rmse",
        )
        job.run(
            dataset=dataset,
            target_column=request.target_column,
            budget_milli_node_hours=request.budget_milli_node_hours,
            model_display_name=request.model_display_name,
            sync=False,
        )
        return str(job.resource_name)


def execute_request(
    request: TabularAutoMLRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _AutoMLClient,
) -> str:
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return request.dataset_name
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    job_name = str(client_factory().start_training(request))
    print(f"started AutoML training job: {job_name}")
    return job_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--target-column", required=True)
    parser.add_argument("--budget-milli-node-hours", type=int, required=True)
    parser.add_argument("--model-display-name", required=True)
    parser.add_argument("--training-job-display-name", required=True)
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
            args.dataset_name,
            args.target_column,
            args.budget_milli_node_hours,
            args.model_display_name,
            args.training_job_display_name,
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
