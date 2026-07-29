"""Plan or explicitly execute tightly scoped Chapter 7 cleanup commands."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Sequence

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")
_SAFE_PREFIXES = (
    "data/nyc-taxi-tip-2022/",
    "data/flowers_photos/",
    "models/nyc-taxi-tip/",
    "models/nyc-taxi-tip-distributed/",
    "models/nyc-taxi-tip-pytorch/",
    "models/flowers_model/",
)


def build_cleanup_commands(
    project_id: str,
    bucket_name: str,
    prefixes: Sequence[str],
    scheduler_job: str | None,
    scheduler_location: str | None,
) -> list[list[str]]:
    """Return validated command arrays; no command is run by this function."""
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project ID must be a lowercase Google Cloud project ID")
    if not _BUCKET_NAME.fullmatch(bucket_name) or ".." in bucket_name:
        raise ValueError("bucket name is not a valid Cloud Storage bucket name")
    if not prefixes and not scheduler_job:
        raise ValueError("choose at least one --prefix or --scheduler-job")

    commands: list[list[str]] = []
    for prefix in prefixes:
        if prefix not in _SAFE_PREFIXES:
            raise ValueError("prefix is not an allowed Chapter 7 cleanup target")
        commands.append(["gcloud", "storage", "rm", "--recursive", f"gs://{bucket_name}/{prefix}"])
    if scheduler_job:
        if not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", scheduler_job):
            raise ValueError("scheduler job name must be a lowercase resource name")
        if not scheduler_location or not re.fullmatch(
            r"[a-z]+(?:-[a-z]+)*[0-9]+", scheduler_location
        ):
            raise ValueError("--scheduler-location is required with --scheduler-job")
        commands.append(
            [
                "gcloud",
                "scheduler",
                "jobs",
                "delete",
                scheduler_job,
                "--project",
                project_id,
                "--location",
                scheduler_location,
                "--quiet",
            ]
        )
    return commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--prefix", action="append", default=[], choices=_SAFE_PREFIXES)
    parser.add_argument("--scheduler-job")
    parser.add_argument("--scheduler-location")
    parser.add_argument("--execute", action="store_true", help="run the displayed commands")
    parser.add_argument("--confirm", help="required literal: DELETE_CH07_RESOURCES")
    return parser


def main(argv: list[str] | None = None, runner: Callable[..., object] = subprocess.run) -> int:
    args = build_parser().parse_args(argv)
    try:
        commands = build_cleanup_commands(
            args.project_id,
            args.bucket_name,
            args.prefix,
            args.scheduler_job,
            args.scheduler_location,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for command in commands:
        print("planned:", " ".join(command))
    if not args.execute:
        print("dry-run: no Google Cloud command was executed")
        return 0
    if args.confirm != "DELETE_CH07_RESOURCES":
        print("error: --execute requires --confirm DELETE_CH07_RESOURCES", file=sys.stderr)
        return 2
    for command in commands:
        runner(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
