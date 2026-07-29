# src/preprocessing.py
"""前処理パイプラインユーティリティ"""
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


def create_preprocessor() -> ColumnTransformer:
    """カテゴリカル・数値特徴量の前処理パイプラインを作成

    Returns:
        ColumnTransformer: 前処理パイプライン
    """
    categorical_features = ["payment_type", "day_of_week", "hour_of_day"]
    numeric_features = ["passenger_count", "trip_distance"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            ),
            ("num", "passthrough", numeric_features),
        ]
    )

    return preprocessor
