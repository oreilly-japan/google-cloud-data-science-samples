"""Generate a local Agent Platform image-import CSV from a flower directory."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")
_LABELS = ("daisy", "dandelion", "roses", "sunflowers", "tulips")


def _validate_bucket_name(value: str) -> str:
    if not _BUCKET_NAME.fullmatch(value) or ".." in value:
        raise ValueError("bucket name is not a valid Cloud Storage bucket name")
    return value


def build_manifest(source_dir: Path, bucket_name: str) -> list[str]:
    """Build deterministic CSV lines without reading images or using any network service."""
    bucket_name = _validate_bucket_name(bucket_name)
    if not source_dir.is_dir():
        raise ValueError(f"source directory does not exist: {source_dir}")
    lines: list[str] = []
    for label in _LABELS:
        label_dir = source_dir / label
        if not label_dir.is_dir():
            raise ValueError(f"missing required label directory: {label}")
        images = sorted(path for path in label_dir.rglob("*.jpg") if path.is_file())
        if not images:
            raise ValueError(f"no .jpg images found for label: {label}")
        for image in images:
            relative = image.relative_to(source_dir).as_posix()
            lines.append(f"gs://{bucket_name}/data/flowers_photos/{relative},{label}")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="show the local write plan only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        lines = build_manifest(args.source_dir, args.bucket_name)
        if args.output.exists() and not args.overwrite:
            raise ValueError("output exists; pass --overwrite to replace it")
        if args.dry_run:
            print(f"dry-run: would write {len(lines)} manifest rows to {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"wrote {len(lines)} manifest rows to {args.output}")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
