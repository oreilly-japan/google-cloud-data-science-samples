# src/cleanup/delete_endpoint.py
# エンドポイントの削除

from google.cloud import aiplatform


def delete_endpoint(
    project_id: str,
    location: str,
    endpoint_display_name: str,
    force: bool = False
):
    """エンドポイントを削除する"""

    aiplatform.init(project=project_id, location=location)

    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"',
        order_by="create_time desc"
    )

    if not endpoints:
        print(f"エンドポイント '{endpoint_display_name}' が見つかりません")
        return

    endpoint = endpoints[0]

    # デプロイされているモデルをアンデプロイ
    deployed_models = endpoint.gca_resource.deployed_models
    if deployed_models:
        print(f"{len(deployed_models)} 個のモデルをアンデプロイしています...")
        for deployed_model in deployed_models:
            endpoint.undeploy(deployed_model_id=deployed_model.id)
            print(f"モデル {deployed_model.id} をアンデプロイしました")

    # エンドポイントを削除
    endpoint.delete(force=force)
    print(f"エンドポイント '{endpoint_display_name}' を削除しました")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    ENDPOINT_DISPLAY_NAME = "nyc-taxi-tip-endpoint"

    delete_endpoint(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        endpoint_display_name=ENDPOINT_DISPLAY_NAME
    )
