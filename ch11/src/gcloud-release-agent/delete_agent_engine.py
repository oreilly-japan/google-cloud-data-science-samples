# delete_agent_engine.py
# デプロイした Agent Runtime（Agent Engine）の削除（書籍未掲載の補足スクリプト）
#
# ハンズオン完了後、デプロイしたエージェントが不要になったら本スクリプトで
# 削除できます。min_instances=0 の設定ではアイドル時の課金は発生しませんが、
# リソースを残したくない場合に使用してください。

import os
from pathlib import Path

from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines

# エージェントディレクトリの .env を読み込む
load_dotenv(Path(__file__).parent / "gcloud_release_agent" / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")


def delete_agent_engine(agent_engine_id: str, force: bool = True):
    """Agent Runtime を削除する

    Args:
        agent_engine_id: projects/.../locations/.../reasoningEngines/... のフルパス
        force: True の場合、紐づくセッションなどの子リソースも併せて削除する
    """

    agent_engine = agent_engines.get(agent_engine_id)
    display_name = agent_engine.gca_resource.display_name
    agent_engine.delete(force=force)
    print(f"Agent Runtime '{display_name}' を削除しました")
    print(f"  {agent_engine_id}")


if __name__ == "__main__":
    if not AGENT_ENGINE_ID:
        print("エラー: 環境変数 AGENT_ENGINE_ID を設定してください")
        exit(1)

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    delete_agent_engine(AGENT_ENGINE_ID)
