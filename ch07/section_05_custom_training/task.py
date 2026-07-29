"""CPU Custom Training 用の NYC Taxi LightGBM トレーナー。

このモジュールはAgent Platform Custom Jobのコンテナから実行することを想定する。
ローカルで ``--dry-run`` を指定した場合は、GCS クライアントも学習用依存関係も
読み込まない。
"""

from __future__ import annotations

import argparse
from typing import Any, Protocol

DEFAULT_DATA_PATH = "data/nyc-taxi-tip-2022/taxi-*.csv"
DEFAULT_MODEL_PATH = "models/nyc-taxi-tip/lgbm_model.joblib"


class FileSystem(Protocol):
    """テストで置き換え可能な GCSFileSystem の最小インターフェース。"""

    def glob(self, path: str) -> list[str]: ...

    def open(self, path: str, mode: str) -> Any: ...


def gcs_uri(bucket_name: str, object_path: str) -> str:
    """検証済みのバケット名とオブジェクト相対パスから GCS URI を作る。"""
    if not bucket_name or bucket_name.startswith("gs://") or "/" in bucket_name:
        raise ValueError("bucket_name は gs:// を除くバケット名だけを指定してください")
    if not object_path or object_path.startswith("gs://") or object_path.startswith("/"):
        raise ValueError("data/model path は gs:// を除く相対パスにしてください")
    if ".." in object_path.split("/"):
        raise ValueError("data/model path に '..' は指定できません")
    return f"gs://{bucket_name}/{object_path}"


def _filesystem() -> FileSystem:
    try:
        import gcsfs
    except ImportError as exc:  # pragma: no cover - 実コンテナでのみ使用
        raise RuntimeError("gcsfs をインストールしてから実行してください") from exc
    return gcsfs.GCSFileSystem()


def train(
    args: argparse.Namespace,
    filesystem: FileSystem | None = None,
    assigned_files: list[str] | None = None,
) -> str:
    """CSV を読み、LightGBM モデルを GCS に保存して保存先 URI を返す。"""
    data_uri = gcs_uri(args.bucket_name, args.data_path)
    model_uri = gcs_uri(args.bucket_name, args.model_path)
    if args.dry_run:
        print(f"DRY RUN: data={data_uri}; model={model_uri}")
        return model_uri

    fs = filesystem or _filesystem()
    files = sorted(assigned_files) if assigned_files is not None else sorted(fs.glob(data_uri))
    if not files:
        raise FileNotFoundError(f"CSV が見つかりません: {data_uri}")
    try:
        import joblib
        import lightgbm as lgb
        import pandas as pd
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
        features, columns=["payment_type", "day_of_week", "hour_of_day"], drop_first=True
    )
    train_x, _, train_y, _ = train_test_split(encoded, target, test_size=0.2, random_state=42)
    model = lgb.LGBMRegressor(random_state=42, verbose=-1)
    model.fit(train_x, train_y)
    with fs.open(model_uri, "wb") as stream:
        joblib.dump(model, stream)
    print(f"モデルを保存しました: {model_uri}")
    return model_uri


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYC Taxi の LightGBM CPU トレーナー")
    parser.add_argument("--bucket-name", required=True, help="gs:// を除く GCS バケット名")
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH, help="CSV の GCS 相対 glob")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH, help="モデルの GCS 相対パス")
    parser.add_argument("--dry-run", action="store_true", help="GCS と学習処理を実行せず計画を表示")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    train(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
