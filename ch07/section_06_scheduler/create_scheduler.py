"""Create a Cloud Scheduler HTTP job for an Agent Platform Custom Job body.

Use ``scheduler_validate.py`` first to render the body.  ``--dry-run`` never
loads the Scheduler SDK, creates a client, obtains credentials, or calls Google
Cloud.  Creation requires an explicit billable-operation flag.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LOCATION = re.compile(r"^[a-z]+(?:-[a-z]+)*[0-9]+$")
_JOB_ID = re.compile(r"^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TIME_ZONE = re.compile(r"^[A-Za-z_]+/[A-Za-z_]+$")
_SERVICE_ACCOUNT = re.compile(
    r"^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]"
    r"\.iam\.gserviceaccount\.com$"
)


@dataclass(frozen=True)
class SchedulerRequest:
    project_id: str
    location: str
    job_id: str
    schedule: str
    time_zone: str
    oauth_service_account: str
    custom_job_body: dict[str, object]

    @property
    def parent(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}"

    @property
    def name(self) -> str:
        return f"{self.parent}/jobs/{self.job_id}"

    @property
    def target_uri(self) -> str:
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/customJobs"
        )


def _read_body(path: Path) -> dict[str, object]:
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"body JSON could not be read: {error}") from error
    if not isinstance(body, dict) or not isinstance(body.get("displayName"), str):
        raise ValueError("body JSON must be a rendered Agent Platform CustomJob object")
    if not isinstance(body.get("jobSpec"), dict):
        raise ValueError("body JSON must include jobSpec")
    return body


def build_request(
    project_id: str,
    location: str,
    job_id: str,
    schedule: str,
    time_zone: str,
    oauth_service_account: str,
    custom_job_body: Mapping[str, object],
) -> SchedulerRequest:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    if not _LOCATION.fullmatch(location):
        raise ValueError("location must resemble a Google Cloud region, such as us-central1")
    if not _JOB_ID.fullmatch(job_id):
        raise ValueError("job ID must be a lowercase Scheduler resource name")
    if not schedule or any(character in schedule for character in "\r\n"):
        raise ValueError("schedule must be a one-line cron expression")
    if not _TIME_ZONE.fullmatch(time_zone):
        raise ValueError("time zone must use an IANA form such as Asia/Tokyo")
    if not _SERVICE_ACCOUNT.fullmatch(oauth_service_account):
        raise ValueError("OAuth service account must be a service account email")
    if not isinstance(custom_job_body.get("displayName"), str) or not isinstance(
        custom_job_body.get("jobSpec"), dict
    ):
        raise ValueError("body JSON must be a rendered Agent Platform CustomJob object")
    return SchedulerRequest(
        project_id,
        location,
        job_id,
        schedule,
        time_zone,
        oauth_service_account,
        dict(custom_job_body),
    )


class _SchedulerClient:
    """Late-bound adapter so dry-run works without the optional Scheduler dependency."""

    def __init__(self) -> None:
        try:
            from google.cloud import scheduler_v1
        except ImportError as error:
            raise RuntimeError(
                "install google-cloud-scheduler before creating a Scheduler job"
            ) from error
        self._scheduler_v1 = scheduler_v1
        self._client = scheduler_v1.CloudSchedulerClient()

    def create(self, request: SchedulerRequest) -> str:
        scheduler_v1 = self._scheduler_v1
        job = scheduler_v1.Job(
            name=request.name,
            schedule=request.schedule,
            time_zone=request.time_zone,
            http_target=scheduler_v1.HttpTarget(
                uri=request.target_uri,
                http_method=scheduler_v1.HttpMethod.POST,
                headers={"Content-Type": "application/json"},
                body=json.dumps(request.custom_job_body, separators=(",", ":")).encode("utf-8"),
                oauth_token=scheduler_v1.OAuthToken(
                    service_account_email=request.oauth_service_account
                ),
            ),
        )
        return str(self._client.create_job(parent=request.parent, job=job).name)


def execute_request(
    request: SchedulerRequest,
    *,
    dry_run: bool,
    allow_billable: bool,
    client_factory: Callable[[], Any] = _SchedulerClient,
) -> str:
    if dry_run:
        print("DRY RUN (no auth, client creation, or network):", request)
        return request.name
    if not allow_billable:
        raise PermissionError("non-dry-run requires --allow-billable")
    name = str(client_factory().create(request))
    print(f"created Scheduler job: {name}")
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--time-zone", required=True)
    parser.add_argument("--oauth-service-account", required=True)
    parser.add_argument("--body-json", type=Path, required=True)
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
            args.job_id,
            args.schedule,
            args.time_zone,
            args.oauth_service_account,
            _read_body(args.body_json),
        )
        execute_request(request, dry_run=args.dry_run, allow_billable=args.allow_billable)
    except (PermissionError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
