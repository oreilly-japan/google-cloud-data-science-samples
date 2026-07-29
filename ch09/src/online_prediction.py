# src/online_prediction.py
# オンライン予測関連の関数

import os

import gcsfs
import joblib
import pandas as pd
from google.cloud import aiplatform


def get_endpoint(
    project_id: str,
    location: str,
    endpoint_display_name: str
    ):
    """Endpointを取得する"""

    aiplatform.init(project=project_id, location=location)

    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"',
        order_by="create_time desc"
    )

    endpoint = endpoints[0]
    print(f"Endpointを取得しました: {endpoint.resource_name}")

    return endpoint


def load_preprocessor(bucket_name: str, preprocessor_path: str = "models/preprocessor/preprocessor.joblib"):
    """GCSから前処理器を読み込む"""
    fs = gcsfs.GCSFileSystem()
    preprocessor_gcs_path = f"gs://{bucket_name}/{preprocessor_path}"
    with fs.open(preprocessor_gcs_path, 'rb') as f:
        preprocessor = joblib.load(f)
    return preprocessor


def preprocess_instances(preprocessor, instances: list) -> list:
    """入力インスタンスに前処理を適用する

    XGBoostの事前構築済みコンテナは前処理を行わないため、
    学習時と同じ前処理（OneHotEncoding）を適用してから送信する。
    """
    # インスタンスをDataFrameに変換
    df = pd.DataFrame(instances)

    # 前処理を適用
    transformed = preprocessor.transform(df)

    # リストのリストに変換（Endpointが期待する形式）
    return transformed.tolist()


def predict_online(
    endpoint,
    instances: list
):
    """オンライン予測を実行する"""

    response = endpoint.predict(instances=instances)

    print(f"予測結果:")
    for i, prediction in enumerate(response.predictions):
        print(f"  予測結果 {i+1}: {prediction}")

    return response


def interpret_predictions(response):
    """予測結果を解釈する（回帰モデルなのでチップ額の予測値が直接返る）"""

    print("解釈:")
    for i, prediction in enumerate(response.predictions):
        print(f"  予測結果 {i+1}: 予測チップ額 ${prediction:.2f}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    BUCKET_NAME = os.getenv("BATCH_PREDICT_BUCKET_NAME")
    ENDPOINT_DISPLAY_NAME = "nyc-taxi-tip-endpoint"

    # 前処理器を読み込む
    preprocessor = load_preprocessor(BUCKET_NAME)

    # Endpointを取得
    endpoint = get_endpoint(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        endpoint_display_name=ENDPOINT_DISPLAY_NAME
    )

    # 予測用のデータを作成（学習データの値を参考に複数件設定）
    test_instances = [
        {"passenger_count": 1, "trip_distance": 2.39,  "payment_type": 1, "day_of_week": 7, "hour_of_day": 0},
        {"passenger_count": 5, "trip_distance": 10.23, "payment_type": 1, "day_of_week": 7, "hour_of_day": 0},
    ]

    # 前処理を適用
    preprocessed_instances = preprocess_instances(preprocessor, test_instances)

    # オンライン予測を実行
    response = predict_online(endpoint, preprocessed_instances)

    # 予測結果を解釈
    interpret_predictions(response)
