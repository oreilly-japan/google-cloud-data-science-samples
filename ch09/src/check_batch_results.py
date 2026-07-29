# src/check_batch_results.py
# バッチ予測結果の確認

import json
import os

from dotenv import load_dotenv
from google.cloud import storage


def get_batch_prediction_results(gcs_output_directory: str):
    """バッチ予測結果を取得する"""

    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

    # GCS URIをパース
    parts = gcs_output_directory.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    results = []
    for blob in blobs:
        # 予測結果ファイルを読み込む
        # ファイルは分割出力されるが、サンプルとして先頭ファイル（00000）のみを対象とする
        if "prediction.results-00000" in blob.name:
            content = blob.download_as_text()
            for line in content.strip().split("\n"):
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    return results


if __name__ == "__main__":
    load_dotenv()

    # バッチ予測の出力ディレクトリを環境変数から取得
    # batch_prediction.py 実行時に表示される出力先を .env に設定する
    OUTPUT_DIR = os.getenv("BATCH_PREDICTION_OUTPUT_DIR")

    if not OUTPUT_DIR:
        print("エラー: 環境変数 BATCH_PREDICTION_OUTPUT_DIR を設定してください")
        exit(1)

    print(f"結果を取得中: {OUTPUT_DIR}")
    predictions = get_batch_prediction_results(OUTPUT_DIR)

    print(f"\n予測結果: {len(predictions)}件")
    for i, pred in enumerate(predictions[:10]):
        print(f"  {i+1}: {pred}")
