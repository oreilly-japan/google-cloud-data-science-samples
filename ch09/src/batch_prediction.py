# src/batch_prediction.py
# バッチ予測ジョブの実行

import os

from dotenv import load_dotenv
from google.cloud import aiplatform


def run_batch_prediction(
    project_id: str,
    location: str,
    model_display_name: str,
    gcs_source_uri: str,
    gcs_destination_prefix: str,
    job_display_name: str = "batch-prediction-job"
):
    """バッチ予測ジョブを実行する"""

    aiplatform.init(project=project_id, location=location)

    # Model Registryからモデルを取得
    models = aiplatform.Model.list(
        filter=f'display_name="{model_display_name}"',
        order_by="create_time desc"
    )

    if not models:
        raise ValueError(f"モデル '{model_display_name}' が見つかりません")

    model = models[0]
    print(f"モデルを取得しました: {model.resource_name}")

    # バッチ予測ジョブを作成、実行
    batch_prediction_job = model.batch_predict(
        job_display_name=job_display_name,
        gcs_source=gcs_source_uri,
        gcs_destination_prefix=gcs_destination_prefix,
        instances_format="csv",
        predictions_format="jsonl",
        machine_type="n1-standard-4",
        starting_replica_count=1,
        max_replica_count=1,
        sync=False,  # 非同期で実行
    )

    # リソース作成完了を待機
    batch_prediction_job.wait_for_resource_creation()

    return batch_prediction_job


if __name__ == "__main__":
    load_dotenv()

    # 環境変数から設定を読み込む
    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    BUCKET_NAME = os.getenv("BATCH_PREDICT_BUCKET_NAME")

    # バッチ予測を実行
    MODEL_DISPLAY_NAME = "nyc-taxi-tip-xgboost-model"  # 8章で作成したモデル名
    PREDICTION_DATA_PATH = "prediction_input/taxi_tip_prediction_input.csv"
    GCS_SOURCE_URI = f"gs://{BUCKET_NAME}/{PREDICTION_DATA_PATH}"
    GCS_DESTINATION_PREFIX = f"gs://{BUCKET_NAME}/prediction_output/"

    batch_job = run_batch_prediction(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        model_display_name=MODEL_DISPLAY_NAME,
        gcs_source_uri=GCS_SOURCE_URI,
        gcs_destination_prefix=GCS_DESTINATION_PREFIX,
        job_display_name="nyc-taxi-tip-batch-prediction"
    )

    # ジョブの完了を待機
    batch_job.wait()
    print(f"バッチ予測ジョブが完了しました")
    print(f"出力先: {batch_job.output_info.gcs_output_directory}")
