# src/prepare_data.py
# 予測用データの準備

import os
from io import StringIO

import gcsfs
import joblib
import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage


def prepare_prediction_data(
    bucket_name: str,
    data_path: str,
    output_path: str,
    preprocessor_path: str = "models/preprocessor/preprocessor.joblib",
):
    """8章のデータから末尾10%を予測用データとして準備し、GCSに保存する"""

    # 8章で保存した前処理器を読み込む
    fs = gcsfs.GCSFileSystem()
    preprocessor_gcs_path = f"gs://{bucket_name}/{preprocessor_path}"
    print(f"前処理器を読み込み中: {preprocessor_gcs_path}")
    with fs.open(preprocessor_gcs_path, "rb") as f:
        preprocessor = joblib.load(f)

    # GCS からデータを読み込む
    gcs_path_pattern = f"gs://{bucket_name}/{data_path}"
    file_list = fs.glob(gcs_path_pattern)

    # 全ファイルを読み込んで結合
    df_list = [pd.read_csv(f"gs://{file}") for file in file_list]
    df = pd.concat(df_list, ignore_index=True)
    print(f"全データを読み込みました（{len(df)}行）")

    # 末尾10%を予測用データとして抽出（8章で前90%を学習に使用）
    prediction_df = df.iloc[int(len(df) * 0.9):][[
        "passenger_count", "trip_distance", "payment_type",
        "day_of_week", "hour_of_day",
    ]]
    print(f"予測用データを抽出しました（末尾10%: {len(prediction_df)}行）")

    # 学習時と同じ前処理（OneHotEncoding）を適用
    print("前処理を適用中...")
    prediction_transformed = preprocessor.transform(prediction_df)
    print(f"前処理後の特徴量数: {prediction_transformed.shape[1]}")

    # 前処理済みデータを DataFrame に変換
    # XGBoost コンテナは CSV の数値データを期待する
    prediction_transformed_df = pd.DataFrame(prediction_transformed)

    # ヘッダーなし CSV として GCS にアップロード
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(output_path)

    csv_buffer = StringIO()
    prediction_transformed_df.to_csv(csv_buffer, index=False, header=False)
    blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")

    print(f"前処理済み予測用データをgs://{bucket_name}/{output_path}に保存しました")

    return prediction_transformed


if __name__ == "__main__":
    load_dotenv()

    # 予測用データを準備
    BUCKET_NAME = os.getenv("BATCH_PREDICT_BUCKET_NAME")
    DATA_PATH = "data/nyc-taxi-tip-2022/taxi-*.csv"  # 8章と同じデータパス
    PREDICTION_DATA_PATH = "prediction_input/taxi_tip_prediction_input.csv"

    prepare_prediction_data(
        bucket_name=BUCKET_NAME,
        data_path=DATA_PATH,
        output_path=PREDICTION_DATA_PATH,
    )
