"""Validate and render the Chapter 7 Cloud Scheduler request body offline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PLACEHOLDER = re.compile(r"\$\{([A-Z_]+)\}")
_SERVICE_ACCOUNT = re.compile(
    r"^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]"
    r"\.iam\.gserviceaccount\.com$"
)
_RUN_ID = re.compile(r"^[0-9]{8}-[a-z0-9]{4}$")
_REQUIRED = {
    "JOB_DISPLAY_NAME",
    "IMAGE_URI",
    "BUCKET_NAME",
    "RUNTIME_SERVICE_ACCOUNT",
    "RUN_ID",
}


def parse_assignments(items: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--set must use KEY=VALUE")
        key, value = item.split("=", 1)
        if key not in _REQUIRED:
            raise ValueError(f"unsupported placeholder: {key}")
        if not value or value.startswith("<"):
            raise ValueError(f"{key} must have a non-placeholder value")
        values[key] = value
    missing = _REQUIRED - values.keys()
    if missing:
        raise ValueError("missing values for: " + ", ".join(sorted(missing)))
    if not _SERVICE_ACCOUNT.fullmatch(values["RUNTIME_SERVICE_ACCOUNT"]):
        raise ValueError("RUNTIME_SERVICE_ACCOUNT must be a service account email")
    if not _RUN_ID.fullmatch(values["RUN_ID"]):
        raise ValueError("RUN_ID must use YYYYMMDD-xxxx")
    return values


def render_payload(values: dict[str, str], template_path: Path | None = None) -> dict[str, object]:
    """Render the checked template as JSON. This function does not contact Google Cloud."""
    missing = _REQUIRED - values.keys()
    if missing:
        raise ValueError("missing values for: " + ", ".join(sorted(missing)))
    if not _SERVICE_ACCOUNT.fullmatch(values["RUNTIME_SERVICE_ACCOUNT"]):
        raise ValueError("RUNTIME_SERVICE_ACCOUNT must be a service account email")
    if not _RUN_ID.fullmatch(values["RUN_ID"]):
        raise ValueError("RUN_ID must use YYYYMMDD-xxxx")
    path = template_path or Path(__file__).with_name("scheduler-job-body.json")
    rendered = path.read_text(encoding="utf-8")
    for key in _REQUIRED:
        value = values[key]
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} must be a non-empty string")
        rendered = rendered.replace("${" + key + "}", value)
    unresolved = _PLACEHOLDER.findall(rendered)
    if unresolved:
        raise ValueError("unresolved placeholders: " + ", ".join(sorted(set(unresolved))))
    payload = json.loads(rendered)
    if not isinstance(payload.get("displayName"), str):
        raise ValueError("payload.displayName must be a string")
    labels = payload.get("labels")
    if not isinstance(labels, dict) or labels.get("sample-run") != values["RUN_ID"]:
        raise ValueError("payload must include the sample run label")
    job_spec = payload.get("jobSpec")
    if not isinstance(job_spec, dict):
        raise ValueError("payload.jobSpec must be an object")
    if job_spec.get("serviceAccount") != values["RUNTIME_SERVICE_ACCOUNT"]:
        raise ValueError("payload.jobSpec.serviceAccount must match the configured runtime account")
    scheduling = job_spec.get("scheduling")
    if not isinstance(scheduling, dict) or scheduling.get("timeout") != "1800s":
        raise ValueError("payload.jobSpec.scheduling.timeout must be exactly 1800s")
    if scheduling.get("restartJobOnWorkerRestart") is not False:
        raise ValueError("payload must disable restartJobOnWorkerRestart")
    pools = job_spec.get("workerPoolSpecs", [])
    if not isinstance(pools, list) or len(pools) != 1:
        raise ValueError("payload must contain exactly one worker pool")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = render_payload(parse_assignments(args.set))
    except (ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
