# src/cleanup/delete_model.py
# モデルの削除

from google.cloud import aiplatform


def delete_model(
    project_id: str,
    location: str,
    model_display_name: str
):
    """モデルを削除する"""

    aiplatform.init(project=project_id, location=location)

    models = aiplatform.Model.list(
        filter=f'display_name="{model_display_name}"',
        order_by="create_time desc"
    )

    if not models:
        print(f"モデル '{model_display_name}' が見つかりません")
        return

    # 8章から通しで実行すると同名モデルが複数登録されるため、全件を削除する
    for model in models:
        # エンドポイントにデプロイされている場合は削除できないため確認
        try:
            model.delete()
            print(f"モデル '{model_display_name}' ({model.name}) を削除しました")
        except Exception as e:
            print(f"モデルの削除に失敗しました: {e}")
            print("モデルがエンドポイントにデプロイされている場合は、先にアンデプロイしてください")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    MODEL_DISPLAY_NAME = "nyc-taxi-tip-xgboost-model"

    delete_model(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        model_display_name=MODEL_DISPLAY_NAME
    )
