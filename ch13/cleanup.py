"""Explicitly guarded deletion helper for Studies created by this sample."""

from __future__ import annotations

import argparse
from typing import Protocol

from vizier_runner import create_vizier_client, validate_study_name


class StudyDeletionClient(Protocol):
    def delete_study(self, *, name: str) -> object: ...


def validate_cleanup_location(study_name: str, location: str) -> None:
    validate_study_name(study_name)
    parts = study_name.split("/")
    if parts[3] != location:
        raise ValueError("--location must match the location in --study-name")


def delete_study(
    *,
    client: StudyDeletionClient | None,
    study_name: str,
    location: str,
    confirm_delete: bool,
    dry_run: bool,
) -> str:
    """Delete exactly one fully qualified Study only after explicit confirmation."""
    validate_cleanup_location(study_name, location)
    if dry_run:
        return f"DRY RUN: would delete {study_name}"
    if not confirm_delete:
        raise ValueError("refusing deletion: pass --confirm-delete")
    if client is None:
        raise ValueError("a Vizier client is required for deletion")
    client.delete_study(name=study_name)
    return f"Delete requested: {study_name}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete one Chapter 13 Vizier Study")
    parser.add_argument("--study-name", required=True, help="full Study resource name")
    parser.add_argument(
        "--location", required=True, help="Study location, used only after confirmation"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-delete", action="store_true", help="required to issue delete_study"
    )
    args = parser.parse_args(argv)
    try:
        validate_cleanup_location(args.study_name, args.location)
        if not args.dry_run and not args.confirm_delete:
            raise ValueError("refusing deletion: pass --confirm-delete")
        client = None if args.dry_run else create_vizier_client(args.location)
        print(
            delete_study(
                client=client,
                study_name=args.study_name,
                location=args.location,
                confirm_delete=args.confirm_delete,
                dry_run=args.dry_run,
            )
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
