"""HPT trial 用のメトリクス報告を、SDK から分離する。"""

from __future__ import annotations

import argparse
import math
from collections.abc import Callable

from task import DEFAULT_DATA_PATH, FileSystem, _filesystem, gcs_uri

METRIC_ID = "rmse"


def report_rmse(value: float, reporter: Callable[[str, float, int], None] | None = None) -> None:
    """有限かつ非負の RMSE だけを HPT に送る。テストでは reporter を注入する。"""
    if not math.isfinite(value) or value < 0:
        raise ValueError("RMSE は 0 以上の有限値である必要があります")
    if reporter is None:
        try:
            import hypertune
        except ImportError as exc:  # pragma: no cover - 実コンテナでのみ使用
            raise RuntimeError("cloudml-hypertune をインストールしてください") from exc
        client = hypertune.HyperTune()

        def default_reporter(metric_id: str, metric_value: float, step: int) -> None:
            client.report_hyperparameter_tuning_metric(
                hyperparameter_metric_tag=metric_id,
                metric_value=metric_value,
                global_step=step,
            )

        reporter = default_reporter
    reporter(METRIC_ID, value, 1)


def train(
    args: argparse.Namespace,
    filesystem: FileSystem | None = None,
    reporter: Callable[[str, float, int], None] | None = None,
) -> float | None:
    """1 trial を学習・評価し、その RMSE を HPT に報告する。"""
    if args.learning_rate <= 0 or args.num_leaves < 2:
        raise ValueError("learning-rate は正数、num-leaves は 2 以上にしてください")
    data_uri = gcs_uri(args.bucket_name, args.data_path)
    if args.dry_run:
        print(
            "DRY RUN: "
            f"data={data_uri}; learning_rate={args.learning_rate}; num_leaves={args.num_leaves}"
        )
        return None
    fs = filesystem or _filesystem()
    files = sorted(fs.glob(data_uri))
    if not files:
        raise FileNotFoundError(f"CSV が見つかりません: {data_uri}")
    try:
        import lightgbm as lgb
        import pandas as pd
        from sklearn.metrics import mean_squared_error
        from sklearn.model_selection import train_test_split
    except ImportError as exc:  # pragma: no cover - 実コンテナでのみ使用
        raise RuntimeError("requirements.txt の学習依存関係をインストールしてください") from exc
    frame = pd.concat([pd.read_csv(f"gs://{path}") for path in files], ignore_index=True)
    required = {"tip_amount", "pickup_datetime", "payment_type", "day_of_week", "hour_of_day"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"入力 CSV に必要な列がありません: {', '.join(missing)}")
    features = frame.drop(columns=["tip_amount", "pickup_datetime"])
    target = frame["tip_amount"]
    encoded = pd.get_dummies(
        features,
        columns=["payment_type", "day_of_week", "hour_of_day"],
        drop_first=True,
    )
    train_x, test_x, train_y, test_y = train_test_split(
        encoded, target, test_size=0.2, random_state=42
    )
    model = lgb.LGBMRegressor(
        random_state=42,
        learning_rate=args.learning_rate,
        num_leaves=args.num_leaves,
        verbose=-1,
    )
    model.fit(train_x, train_y)
    rmse = math.sqrt(mean_squared_error(test_y, model.predict(test_x)))
    report_rmse(rmse, reporter)
    print(f"{METRIC_ID}={rmse:.6f}")
    return rmse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LightGBM HPT trial trainer")
    parser.add_argument("--bucket-name", required=True, help="gs:// を除く GCS バケット名")
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH, help="CSV の GCS 相対 glob")
    parser.add_argument(
        "--learning-rate", "--learning_rate", dest="learning_rate", type=float, default=0.1
    )
    parser.add_argument("--num-leaves", "--num_leaves", dest="num_leaves", type=int, default=31)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    train(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
