# src/pipeline/pipeline.py
import os
from dotenv import load_dotenv
import kfp
from kfp import dsl
from google.cloud import aiplatform
from google_cloud_pipeline_components.v1.model import ModelUploadOp
from google_cloud_pipeline_components.types import artifact_types

load_dotenv()

project_id = os.getenv("PROJECT_ID")
pipeline_root_path = os.getenv("PIPELINE_ROOT")
project_region = "asia-northeast1"
pipeline_name = "nyc-taxi-tip-prediction-pipeline"
model_display_name = "nyc-taxi-tip-xgboost-model"

# 事前構築済み推論コンテナ（詳細は9章を参照）
serving_container_uri = "asia-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.2-1:latest"


@dsl.component(
    packages_to_install=[
        "xgboost==2.1.4",
        "pandas==2.2.3",
        "scikit-learn==1.6.1",
        "gcsfs==2025.3.2",
        "joblib==1.4.2",
    ],
    base_image="python:3.11-slim",
)
def train_xgboost(
    bucket_name: str,
    data_path: str,
    learning_rate: float,
    max_depth: int,
    n_estimators: int,
    model_uri: dsl.OutputPath(str),
    metrics: dsl.Output[dsl.Metrics],
):
    """XGBoostモデルを学習して保存する"""
    import pandas as pd
    import xgboost as xgb
    import gcsfs
    import joblib
    import numpy as np
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder

    # GCSからデータを読み込む
    fs = gcsfs.GCSFileSystem()
    gcs_path_pattern = f"gs://{bucket_name}/{data_path}"
    file_list = fs.glob(gcs_path_pattern)

    if not file_list:
        raise FileNotFoundError(f"No files found: {gcs_path_pattern}")

    # 全ファイルを読み込んで結合
    print(f"Found {len(file_list)} files. Loading all files...")
    df_list = [pd.read_csv(f"gs://{file}") for file in file_list]
    df = pd.concat(df_list, ignore_index=True)
    print(f"Loaded {len(df)} rows")

    # 末尾10%は9章の予測用に残すため、前90%のみを使用
    train_size = int(len(df) * 0.9)
    df = df.iloc[:train_size]
    print(f"Using first 90% for training: {len(df)} rows")

    # 特徴量とターゲットを分離
    X = df.drop(columns=['tip_amount'])
    y = df['tip_amount']

    # データ分割（学習用: 80%, 検証用: 10%, テスト用: 10%）
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    print(f"Train: {len(X_train)}, Validation: {len(X_val)}, Test: {len(X_test)}")

    # 前処理パイプライン
    categorical_features = ['payment_type', 'day_of_week', 'hour_of_day']
    numeric_features = ['passenger_count', 'trip_distance']

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', 'passthrough', numeric_features)
        ]
    )

    # 前処理を適用
    print("Applying preprocessing...")
    X_train_transformed = preprocessor.fit_transform(X_train)
    X_val_transformed = preprocessor.transform(X_val)
    X_test_transformed = preprocessor.transform(X_test)

    # XGBoostモデルの学習
    print("Training XGBoost model...")
    xgb_model = xgb.XGBRegressor(
        random_state=42,
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators,
        verbosity=0
    )
    xgb_model.fit(X_train_transformed, y_train)

    # 評価（検証データ）
    y_val_pred = xgb_model.predict(X_val_transformed)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
    print(f"Validation RMSE: {val_rmse:.4f}")

    # 評価（テストデータ）
    y_test_pred = xgb_model.predict(X_test_transformed)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    print(f"Test RMSE: {test_rmse:.4f}")

    # メトリクスを記録（Agent Platform Experimentsで確認可能）
    metrics.log_metric("validation_rmse", val_rmse)
    metrics.log_metric("test_rmse", test_rmse)
    metrics.log_metric("learning_rate", learning_rate)
    metrics.log_metric("max_depth", max_depth)
    metrics.log_metric("n_estimators", n_estimators)

    # XGBoostモデルを .bst形式で保存（事前構築済みコンテナが期待する形式）
    # save_modelはファイルパスを期待するため、一時ファイルに保存してからGCSにコピー
    import tempfile
    model_gcs_path = f"gs://{bucket_name}/models/xgboost/model.bst"
    with tempfile.NamedTemporaryFile(suffix='.bst', delete=False) as tmp:
        xgb_model.save_model(tmp.name)
        fs.put(tmp.name, model_gcs_path)
    print(f"XGBoost model saved to {model_gcs_path}")

    # 前処理器を別ディレクトリに保存（モデルディレクトリにはmodel.bstのみを配置）
    preprocessor_gcs_path = f"gs://{bucket_name}/models/preprocessor/preprocessor.joblib"
    with fs.open(preprocessor_gcs_path, 'wb') as f:
        joblib.dump(preprocessor, f)
    print(f"Preprocessor saved to {preprocessor_gcs_path}")

    # モデルのURIを出力（ディレクトリパス）
    model_dir = f"gs://{bucket_name}/models/xgboost"
    with open(model_uri, 'w') as f:
        f.write(model_dir)


@kfp.dsl.pipeline(
    name=pipeline_name,
    pipeline_root=pipeline_root_path)
def pipeline(
    project_id: str,
    region: str,
    model_display_name: str,
    serving_container_uri: str,
    bucket_name: str,
    data_path: str = "data/nyc-taxi-tip-2022/taxi-*.csv",
    learning_rate: float = 0.1,
    max_depth: int = 6,
    n_estimators: int = 100,
):
    # XGBoostモデルの学習
    training_task = train_xgboost(
        bucket_name=bucket_name,
        data_path=data_path,
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators,
    ).set_memory_limit('32G').set_cpu_limit('4')

    # モデルをインポート
    import_model_task = dsl.importer(
        artifact_uri=training_task.outputs["model_uri"],
        artifact_class=artifact_types.UnmanagedContainerModel,
        metadata={
            "containerSpec": {
                "imageUri": serving_container_uri,
            },
        },
    )

    # モデルのアップロード
    model_upload = ModelUploadOp(
        project=project_id,
        location=region,
        display_name=model_display_name,
        unmanaged_container_model=import_model_task.output,
    )

from kfp import compiler

YOUR_YAML_FILE_PATH = 'src/pipeline_config/nyc_taxi_tip_pipeline.yaml'

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path=YOUR_YAML_FILE_PATH
    )
