"""Create an Image Dataset from an explicitly supplied Cloud Storage manifest."""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LOCATION = re.compile(r"^[a-z]+(?:-[a-z]+)*[0-9]+$")
_DISPLAY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,127}$")
_GCS_MANIFEST = re.compile(r"^gs://[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]/[^*?\s]+\.csv$")
_IMPORT_SCHEMA = "gs://google-cloud-aiplatform/schema/dataset/ioformat/image/single_label_classification_io_format_1.0.0.yaml"


@dataclass(frozen=True)
class ImageDatasetRequest:
    project_id: str
    location: str
    display_name: str
    manifest_uri: str


def build_request(
    project_id: str, location: str, display_name: str, manifest_uri: str
) -> ImageDatasetRequest:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    if not _LOCATION.fullmatch(location):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    if not _DISPLAY_NAME.fullmatch(display_name):
        raise ValueError(
            "display name must be 1-128 letters, numbers, spaces, underscores, or hyphens"
        )
    if not _GCS_MANIFEST.fullmatch(manifest_uri):
        raise ValueError("manifest URI must be a non-wildcard gs://BUCKET/path.csv URI")
    return ImageDatasetRequest(project_id, location, display_name, manifest_uri)


class _ImageDatasetClient:
    def __init__(self) -> None:
        from google.cloud import aiplatform

        self._aiplatform = aiplatform

    def create(self, request: ImageDatasetRequest) -> str:
        self._aiplatform.init(project=request.project_id, location=request.location)
        dataset = self._aiplatform.ImageDataset.create(
            display_name=request.display_name,
            gcs_source=request.manifest_uri,
            import_schema_uri=_IMPORT_SCHEMA,
            sync=False,
        )
        return str(dataset.resource_name)


def execute_request(
    request: ImageDatasetRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _ImageDatasetClient,
) -> str:
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return f"projects/{request.project_id}/locations/{request.location}"
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    name = str(client_factory().create(request))
    print(f"created image dataset: {name}")
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--manifest-uri", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-billable", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        request = build_request(
            args.project_id, args.location, args.display_name, args.manifest_uri
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
