"""Start AutoML image-classification training from an existing Image Dataset."""

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


@dataclass(frozen=True)
class ImageAutoMLRequest:
    project_id: str
    location: str
    dataset_name: str
    model_display_name: str
    training_job_display_name: str
    budget_milli_node_hours: int


def build_request(
    project_id: str,
    location: str,
    dataset_name: str,
    model_display_name: str,
    training_job_display_name: str,
    budget_milli_node_hours: int,
) -> ImageAutoMLRequest:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    if not _LOCATION.fullmatch(location):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    expected = f"projects/{project_id}/locations/{location}/datasets/"
    if not dataset_name.startswith(expected) or not _RESOURCE_ID.fullmatch(
        dataset_name.removeprefix(expected)
    ):
        raise ValueError(
            "dataset name must be an Image Dataset resource in the supplied project and location"
        )
    if not _DISPLAY_NAME.fullmatch(model_display_name) or not _DISPLAY_NAME.fullmatch(
        training_job_display_name
    ):
        raise ValueError(
            "display names must be 1-128 letters, numbers, spaces, underscores, or hyphens"
        )
    if budget_milli_node_hours < 8_000:
        raise ValueError("image AutoML budget must be at least 8000 milli node hours")
    return ImageAutoMLRequest(
        project_id,
        location,
        dataset_name,
        model_display_name,
        training_job_display_name,
        budget_milli_node_hours,
    )


class _ImageAutoMLClient:
    def __init__(self) -> None:
        from google.cloud import aiplatform

        self._aiplatform = aiplatform

    def start_training(self, request: ImageAutoMLRequest) -> str:
        self._aiplatform.init(project=request.project_id, location=request.location)
        dataset = self._aiplatform.ImageDataset(request.dataset_name)
        job = self._aiplatform.AutoMLImageTrainingJob(
            display_name=request.training_job_display_name,
            prediction_type="classification",
            multi_label=False,
            model_type="CLOUD",
        )
        job.run(
            dataset=dataset,
            model_display_name=request.model_display_name,
            budget_milli_node_hours=request.budget_milli_node_hours,
            sync=False,
        )
        return str(job.resource_name)


def execute_request(
    request: ImageAutoMLRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _ImageAutoMLClient,
) -> str:
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return request.dataset_name
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    job_name = str(client_factory().start_training(request))
    print(f"started image AutoML training job: {job_name}")
    return job_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--model-display-name", required=True)
    parser.add_argument("--training-job-display-name", required=True)
    parser.add_argument("--budget-milli-node-hours", type=int, required=True)
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
            args.model_display_name,
            args.training_job_display_name,
            args.budget_milli_node_hours,
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
