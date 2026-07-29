# src/cleanup/delete_training_resources.py
# 8章で作成した学習リソースの削除（書籍未掲載の補足スクリプト）
#
# 書籍 9.8 節のクリーンアップ手順では、9章で作成した Endpoint・モデル・
# バッチ予測ジョブ・予測データが削除対象です。本スクリプトは、それらに
# 含まれない 8章由来のリソース（実験用モデル・学習成果物・コンテナ
# イメージ）をまとめて削除します。

from google.cloud import aiplatform
from google.cloud import artifactregistry_v1
from google.cloud import storage


def delete_models_by_prefix(project_id: str, location: str, display_name_prefix: str):
    """表示名が指定のプレフィックスで始まるモデルをすべて削除する"""

    aiplatform.init(project=project_id, location=location)

    targets = [
        m for m in aiplatform.Model.list()
        if m.display_name.startswith(display_name_prefix)
    ]

    if not targets:
        print(f"'{display_name_prefix}' で始まるモデルが見つかりません")
        return

    for model in targets:
        try:
            model.delete()
            print(f"モデル '{model.display_name}' を削除しました")
        except Exception as e:
            print(f"モデル '{model.display_name}' の削除に失敗しました: {e}")


def delete_gcs_folder(project_id: str, bucket_name: str, prefix: str):
    """GCS フォルダを削除する"""

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    deleted_count = 0
    for blob in bucket.list_blobs(prefix=prefix):
        blob.delete()
        deleted_count += 1

    if deleted_count > 0:
        print(f"フォルダ '{prefix}' を削除しました（{deleted_count} ファイル）")
    else:
        print(f"フォルダ '{prefix}' にファイルが見つかりません")


def delete_experiment(project_id: str, location: str, experiment_name: str):
    """Vertex AI Experiments の実験（配下のランを含む）を削除する"""

    aiplatform.init(project=project_id, location=location)

    try:
        experiment = aiplatform.Experiment(experiment_name)
        experiment.delete()
        print(f"実験 '{experiment_name}' を削除しました")
    except Exception as e:
        print(f"実験 '{experiment_name}' の削除に失敗しました: {e}")


def delete_pipeline_artifacts(project_id: str, bucket_name: str):
    """パイプライン実行アーティファクト（バケット直下のプロジェクト番号フォルダ）を削除する"""

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    # バケット直下のフォルダのうち、名前が数字のみのもの（= プロジェクト番号）が対象
    iterator = bucket.list_blobs(delimiter="/")
    list(iterator)  # prefixes を取得するために一度イテレートする
    for prefix in iterator.prefixes:
        if prefix.rstrip("/").isdigit():
            delete_gcs_folder(project_id, bucket_name, prefix)


def delete_artifact_repository(project_id: str, location: str, repository_id: str):
    """Artifact Registry のリポジトリを削除する"""

    client = artifactregistry_v1.ArtifactRegistryClient()
    name = f"projects/{project_id}/locations/{location}/repositories/{repository_id}"

    try:
        client.delete_repository(name=name).result()
        print(f"Artifact Registry リポジトリ '{repository_id}' を削除しました")
    except Exception as e:
        print(f"リポジトリ '{repository_id}' の削除に失敗しました: {e}")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    PIPELINE_ROOT = os.getenv("PIPELINE_ROOT")
    BUCKET_NAME = PIPELINE_ROOT.replace("gs://", "").rstrip("/").split("/")[0]

    # 8章の実験（8.7節）で作成されたモデル
    print("実験用モデルを削除...")
    delete_models_by_prefix(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        display_name_prefix="nyc-taxi-tip-xgboost-model-depth-",
    )

    # 学習で保存されたモデルと前処理器
    print("\n学習成果物を削除...")
    delete_gcs_folder(PROJECT_ID, BUCKET_NAME, "models/")

    # 8.7節の実験（Experiments とラン）
    print("\n実験を削除...")
    delete_experiment(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        experiment_name="xgboost-max-depth-experiment",
    )

    # パイプライン実行アーティファクト
    print("\nパイプライン実行アーティファクトを削除...")
    delete_pipeline_artifacts(PROJECT_ID, BUCKET_NAME)

    # 8.6節でビルドしたコンテナイメージ
    print("\nコンテナイメージを削除...")
    delete_artifact_repository(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        repository_id="pipelines",
    )

    # 学習データも不要であれば削除する（再取得には時間がかかるため既定では残す）
    # delete_gcs_folder(PROJECT_ID, BUCKET_NAME, "data/")
