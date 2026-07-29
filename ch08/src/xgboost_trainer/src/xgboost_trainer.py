# src/xgboost_trainer/src/xgboost_trainer.py
import os
from dotenv import load_dotenv
from kfp import dsl
from kfp.dsl import Metrics, Output

load_dotenv()
project_id = os.getenv("PROJECT_ID")


@dsl.component(
    base_image="python:3.11-slim",
    target_image=f"asia-northeast1-docker.pkg.dev/{project_id}/pipelines/xgboost-trainer:latest",
    packages_to_install=[
        "xgboost==2.1.4",
        "pandas==2.2.3",
        "scikit-learn==1.6.1",
        "gcsfs==2025.3.2",
        "joblib==1.4.2",
        "python-dotenv",
    ],
)
def train_xgboost(
    bucket_name: str,
    data_path: str,
    learning_rate: float,
    max_depth: int,
    n_estimators: int,
    model_uri: dsl.OutputPath(str),
    metrics: Output[Metrics],
):
    """XGBoostモデルを学習して保存する"""
    import gcsfs

    # ヘルパーモジュールをインポート
    from data_utils import load_data_from_gcs, split_data, train_val_test_split
    from model_utils import evaluate_model, save_model_to_gcs, train_model
    from preprocessing import create_preprocessor

    # GCSファイルシステムの初期化
    fs = gcsfs.GCSFileSystem()

    # データ読み込み
    df = load_data_from_gcs(bucket_name, data_path, fs)

    # 学習用データを分割（末尾10%は9章用に残す）
    df_train = split_data(df, train_ratio=0.9)

    # 特徴量とターゲットを分離
    X = df_train.drop(columns=["tip_amount"])
    y = df_train["tip_amount"]

    # データ分割（学習用: 80%, 検証用: 10%, テスト用: 10%）
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(
        X, y, val_ratio=0.1, test_ratio=0.1
    )

    # 前処理パイプライン作成
    preprocessor = create_preprocessor()

    # モデル学習（前処理を適用してから学習）
    model, preprocessor, _ = train_model(
        X_train, y_train, preprocessor, learning_rate, max_depth, n_estimators
    )

    # 評価（前処理を適用してから評価）
    X_val_transformed = preprocessor.transform(X_val)
    X_test_transformed = preprocessor.transform(X_test)
    val_rmse = evaluate_model(model, X_val_transformed, y_val, "Validation")
    test_rmse = evaluate_model(model, X_test_transformed, y_test, "Test")

    # メトリクスを記録（Agent Platform Experimentsで確認可能）
    metrics.log_metric("validation_rmse", val_rmse)
    metrics.log_metric("test_rmse", test_rmse)
    metrics.log_metric("learning_rate", learning_rate)
    metrics.log_metric("max_depth", max_depth)
    metrics.log_metric("n_estimators", n_estimators)

    # モデルと前処理器を保存
    model_dir = save_model_to_gcs(model, preprocessor, bucket_name, fs)

    # モデルのURIを出力
    with open(model_uri, "w") as f:
        f.write(model_dir)
