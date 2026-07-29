"""第Ⅱ部 6章（Feature Store）のハンズオンで作成したリソースを一括削除するスクリプト。

ノートブック末尾のクリーンアップセルと同等の処理を行います。
環境変数を設定しない場合は、下記の定数の値が使用されます。

削除ステップ:
    1. FeatureView を削除（force=True により関連する同期ジョブも削除）
    2. FeatureOnlineStore を削除（force=True により残存するFeatureViewも一括削除）
    3. FeatureGroup を削除（force=True により配下のFeature、FeatureMonitorも一括削除）
    4. BigQuery データセットを削除（delete_contents=True によりテーブルも一括削除）
"""

import os

import vertexai
from google.cloud import bigquery
from vertexai.resources.preview import feature_store

# --- 設定（環境変数が優先されます） ---
PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
LOCATION = os.environ.get("LOCATION", "us-central1")

# --- リソース名の定数（ノートブックと同じ値） ---
BQ_DATASET_ID = "features"
FEATURE_ONLINE_STORE_ID = "taxi_online_store"
FEATURE_GROUP_ID = "zone_stats"
FEATURE_VIEW_IDS = [
    "zone_stats_registry_view",
    # 継続的同期のシミュレーションを実行した場合に作成されるFeatureView
    "zone_stats_continuous_view",
]


def delete_feature_views() -> None:
    """1. FeatureView の削除（force=True により関連する同期ジョブも削除）"""
    for fv_id in FEATURE_VIEW_IDS:
        try:
            fv = feature_store.FeatureView(
                fv_id, feature_online_store_id=FEATURE_ONLINE_STORE_ID
            )
            try:
                fv.delete(force=True)
            except TypeError:
                # force 未対応のSDKバージョンでは通常削除
                fv.delete()
            print(f"  FeatureView 削除完了: {fv_id}")
        except Exception as e:  # noqa: BLE001
            print(f"  FeatureView 削除スキップ ({fv_id}): {e}")


def delete_feature_online_store() -> None:
    """2. FeatureOnlineStore の削除（force=True により残存するFeatureViewも一括削除）"""
    try:
        fos = feature_store.FeatureOnlineStore(FEATURE_ONLINE_STORE_ID)
        fos.delete(force=True)
        print(f"  FeatureOnlineStore 削除完了: {FEATURE_ONLINE_STORE_ID}")
    except Exception as e:  # noqa: BLE001
        print(f"  FeatureOnlineStore 削除スキップ: {e}")


def delete_feature_group() -> None:
    """3. FeatureGroup の削除（force=True により配下のFeature、FeatureMonitorも一括削除）"""
    try:
        fg = feature_store.FeatureGroup(FEATURE_GROUP_ID)
        fg.delete(force=True)
        print(f"  FeatureGroup 削除完了: {FEATURE_GROUP_ID}")
    except Exception as e:  # noqa: BLE001
        print(f"  FeatureGroup 削除スキップ: {e}")


def delete_bq_dataset() -> None:
    """4. BigQuery データセットの削除（delete_contents=True によりテーブルも一括削除）"""
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        bq_client.delete_dataset(
            f"{PROJECT_ID}.{BQ_DATASET_ID}",
            delete_contents=True,
            not_found_ok=True,
        )
        print(f"  BigQuery データセット削除完了: {BQ_DATASET_ID}")
    except Exception as e:  # noqa: BLE001
        print(f"  BigQuery 削除スキップ: {e}")


def main() -> None:
    if PROJECT_ID == "your-project-id":
        raise SystemExit(
            "PROJECT_ID を設定してください "
            "(例: PROJECT_ID=my-project python3 clean_up.py)"
        )

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print(f"リソースを削除します (project={PROJECT_ID}, location={LOCATION})\n")

    delete_feature_views()
    delete_feature_online_store()
    delete_feature_group()
    delete_bq_dataset()

    print("\nクリーンアップが完了しました")


if __name__ == "__main__":
    main()
