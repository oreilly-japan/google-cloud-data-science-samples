"""GPU Custom Training 用の PyTorch MLP トレーナー。

GPU がない開発機でも ``--dry-run`` と引数検証を実行できる。実学習でのみ
PyTorch、pandas、gcsfs を遅延 import する。
"""

from __future__ import annotations

import argparse
from pathlib import PurePosixPath


def validate_args(args: argparse.Namespace) -> None:
    if not args.bucket_name or args.bucket_name.startswith("gs://") or "/" in args.bucket_name:
        raise ValueError("--bucket-name は gs:// を除くバケット名にしてください")
    for name in ("data_path", "model_dir"):
        value = getattr(args, name)
        if not value or value.startswith(("/", "gs://")) or ".." in PurePosixPath(value).parts:
            raise ValueError(f"--{name.replace('_', '-')} は安全な GCS 相対パスにしてください")
    if args.epochs < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        raise ValueError("epochs と batch-size は 1 以上、learning-rate は正数にしてください")


def train(args: argparse.Namespace) -> str:
    validate_args(args)
    output_uri = f"gs://{args.bucket_name}/{args.model_dir}/dl_model.pth"
    if args.dry_run:
        print(f"DRY RUN: data=gs://{args.bucket_name}/{args.data_path}; model={output_uri}")
        return output_uri
    try:
        import gcsfs
        import pandas as pd
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except ImportError as exc:  # pragma: no cover - 実 GPU コンテナでのみ使用
        raise RuntimeError("GPU コンテナの requirements をインストールしてください") from exc
    filesystem = gcsfs.GCSFileSystem()
    files = sorted(filesystem.glob(f"gs://{args.bucket_name}/{args.data_path}"))
    if not files:
        raise FileNotFoundError("学習 CSV が見つかりません")
    frame = pd.concat([pd.read_csv(f"gs://{path}") for path in files], ignore_index=True)
    required = {
        "tip_amount",
        "pickup_datetime",
        "passenger_count",
        "trip_distance",
        "payment_type",
        "day_of_week",
        "hour_of_day",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"入力 CSV に必要な列がありません: {', '.join(missing)}")
    frame = frame[frame["tip_amount"] < 50]
    features = frame.drop(columns=["tip_amount", "pickup_datetime"])
    target = torch.tensor(frame["tip_amount"].to_numpy(), dtype=torch.float32).reshape(-1, 1)
    preprocessor = ColumnTransformer(
        [
            ("numeric", StandardScaler(), ["passenger_count", "trip_distance"]),
            (
                "category",
                OneHotEncoder(handle_unknown="ignore"),
                ["payment_type", "day_of_week", "hour_of_day"],
            ),
        ]
    )
    matrix = preprocessor.fit_transform(features)
    input_size = matrix.shape[1]

    class MLP(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_size, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, 1),
            )

        def forward(self, value):
            return self.layers(value)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError(
            "GPU が検出されません。GPU Custom Training の worker pool を確認してください"
        )
    model = MLP().to(device)
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    criterion = nn.MSELoss()
    data = torch.tensor(
        matrix.toarray() if hasattr(matrix, "toarray") else matrix, dtype=torch.float32
    )
    for _ in range(args.epochs):
        for index in range(0, len(data), args.batch_size):
            batch_x = data[index : index + args.batch_size].to(device)
            batch_y = target[index : index + args.batch_size].to(device)
            optimizer.zero_grad()
            criterion(model(batch_x), batch_y).sqrt().backward()
            optimizer.step()
    with filesystem.open(output_uri, "wb") as stream:
        torch.save({"model_state_dict": model.state_dict(), "input_size": input_size}, stream)
    return output_uri


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPU PyTorch MLP trainer")
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--data-path", default="data/nyc-taxi-tip-2022/taxi-*.csv")
    parser.add_argument("--model-dir", default="models/nyc-taxi-tip-pytorch")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    train(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
