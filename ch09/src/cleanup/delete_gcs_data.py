# src/cleanup/delete_gcs_data.py
# Cloud Storage データの削除

from google.cloud import storage


def delete_gcs_folder(bucket_name: str, prefix: str):
    """GCS フォルダを削除する"""

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blobs = bucket.list_blobs(prefix=prefix)
    deleted_count = 0
    for blob in blobs:
        blob.delete()
        print(f"  削除: {blob.name}")
        deleted_count += 1

    if deleted_count > 0:
        print(f"フォルダ '{prefix}' を削除しました（{deleted_count} ファイル）")
    else:
        print(f"フォルダ '{prefix}' にファイルが見つかりません")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    BUCKET_NAME = os.getenv("BATCH_PREDICT_BUCKET_NAME")

    # 予測入出力データを削除
    print("予測入力データを削除...")
    delete_gcs_folder(BUCKET_NAME, "prediction_input/")

    print("\n予測出力データを削除...")
    delete_gcs_folder(BUCKET_NAME, "prediction_output/")
