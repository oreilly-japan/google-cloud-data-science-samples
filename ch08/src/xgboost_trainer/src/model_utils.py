# src/model_utils.py
"""モデルの学習・評価・保存ユーティリティ"""
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    preprocessor: ColumnTransformer,
    learning_rate: float,
    max_depth: int,
    n_estimators: int,
) -> tuple:
    """前処理を適用して XGBoost モデルを学習

    Args:
        X_train: 学習用特徴量
        y_train: 学習用ターゲット
        preprocessor: 前処理パイプライン
        learning_rate: 学習率
        max_depth: 木の最大深さ
        n_estimators: 決定木の数

    Returns:
        (学習済みモデル, 学習済み前処理器, 前処理済み学習データ) のタプル
    """
    # 前処理を適用
    print("Applying preprocessing...")
    X_train_transformed = preprocessor.fit_transform(X_train)

    # XGBoost モデルの学習
    print("Training XGBoost model...")
    xgb_model = xgb.XGBRegressor(
        random_state=42,
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators,
        verbosity=0,
    )
    xgb_model.fit(X_train_transformed, y_train)

    return xgb_model, preprocessor, X_train_transformed


def evaluate_model(
    model: xgb.XGBRegressor,
    X: np.ndarray,
    y: pd.Series,
    dataset_name: str,
) -> float:
    """モデルを評価して RMSE を出力

    Args:
        model: 学習済みモデル
        X: 前処理済み特徴量
        y: ターゲット
        dataset_name: データセット名（ログ出力用）

    Returns:
        RMSE 値
    """
    y_pred = model.predict(X)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    print(f"{dataset_name} RMSE: {rmse:.4f}")
    return rmse


def save_model_to_gcs(
    model: xgb.XGBRegressor,
    preprocessor: ColumnTransformer,
    bucket_name: str,
    fs,
) -> str:
    """モデルと前処理器を GCS に保存

    XGBoost の事前構築済み推論コンテナが期待する model.bst 形式でモデルを保存し、
    前処理器は別ディレクトリに preprocessor.joblib として保存する。
    推論時には、クライアント側で前処理を適用してから予測リクエストを送信する。

    Args:
        model: 学習済みモデル
        preprocessor: 学習済み前処理器
        bucket_name: GCS バケット名
        fs: gcsfs.GCSFileSystem インスタンス

    Returns:
        モデルの GCS ディレクトリパス
    """
    # XGBoost モデルを .bst 形式で保存
    model_gcs_path = f"gs://{bucket_name}/models/xgboost/model.bst"
    local_model_path = "/tmp/model.bst"
    model.save_model(local_model_path)
    fs.put(local_model_path, model_gcs_path)
    print(f"XGBoost model saved to {model_gcs_path}")

    # 前処理器を別ディレクトリに保存（モデルディレクトリには model.bst のみを配置）
    preprocessor_gcs_path = f"gs://{bucket_name}/models/preprocessor/preprocessor.joblib"
    with fs.open(preprocessor_gcs_path, "wb") as f:
        joblib.dump(preprocessor, f)
    print(f"Preprocessor saved to {preprocessor_gcs_path}")

    model_dir = f"gs://{bucket_name}/models/xgboost"
    return model_dir
