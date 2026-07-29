"""Analyse Chapter 13 trial results with a local Random Forest surrogate model.

CSV analysis is completely local.  Reading an Experiment is a separate,
explicitly confirmed operation because it contacts Google Cloud.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any


def extract_training_data(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[str], list[list[float]], list[float]]:
    materialized = list(rows)
    if not materialized:
        raise ValueError("no trial rows were supplied")
    feature_names = sorted({key for row in materialized for key in row if key.startswith("param.")})
    if not feature_names:
        raise ValueError("expected one or more param.* columns")
    missing = [
        index
        for index, row in enumerate(materialized, start=1)
        if "metric.cost" not in row or any(name not in row for name in feature_names)
    ]
    if missing:
        raise ValueError(f"rows missing metric.cost or a parameter value: {missing}")
    try:
        features = [[float(row[name]) for name in feature_names] for row in materialized]
        target = [float(row["metric.cost"]) for row in materialized]
    except (TypeError, ValueError) as exc:
        raise ValueError("param.* and metric.cost values must be numeric") from exc
    return feature_names, features, target


def fit_random_forest(
    rows: Iterable[Mapping[str, Any]], *, estimators: int = 100
) -> list[dict[str, float | str]]:
    if estimators < 1:
        raise ValueError("estimators must be at least 1")
    names, features, target = extract_training_data(rows)
    if len(features) < 2:
        raise ValueError("at least two trial rows are required to train a surrogate model")
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise RuntimeError("install scikit-learn to train the surrogate model") from exc
    model = RandomForestRegressor(n_estimators=estimators, random_state=42)
    model.fit(features, target)
    return [
        {"feature": name.removeprefix("param."), "importance": float(importance)}
        for name, importance in sorted(
            zip(names, model.feature_importances_, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() != ".csv":
        raise ValueError("--input-csv must name a .csv file")
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def get_experiment_rows(
    experiment: str, *, fetcher: Callable[[str], Any] | None = None
) -> list[dict[str, Any]]:
    if not experiment.strip():
        raise ValueError("experiment is required")
    if fetcher is None:
        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise RuntimeError(
                "install google-cloud-aiplatform to read Experiments on Agent Platform"
            ) from exc
        fetcher = aiplatform.get_experiment_df
    dataframe = fetcher(experiment)
    return list(dataframe.to_dict(orient="records"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fit a local Random Forest surrogate for Chapter 13 results"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--input-csv", type=Path, help="local CSV containing param.* and metric.cost columns"
    )
    source.add_argument("--experiment", help="Experiments on Agent Platform display name to read")
    parser.add_argument(
        "--confirm-cloud-read",
        action="store_true",
        help="required with --experiment before an API read",
    )
    parser.add_argument("--estimators", type=int, default=100)
    parser.add_argument("--output-json", type=Path, help="write local feature importances as JSON")
    args = parser.parse_args(argv)
    if args.experiment and not args.confirm_cloud_read:
        parser.error("refusing Cloud access: --experiment requires --confirm-cloud-read")
    try:
        rows = (
            read_csv_rows(args.input_csv)
            if args.input_csv
            else get_experiment_rows(args.experiment)
        )
        importance = fit_random_forest(rows, estimators=args.estimators)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    output = json.dumps(importance, indent=2)
    if args.output_json:
        args.output_json.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
