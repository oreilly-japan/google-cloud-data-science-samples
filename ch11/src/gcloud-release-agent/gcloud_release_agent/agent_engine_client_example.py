import asyncio
import os
import uuid

from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines

# .envファイルから環境変数を読み込み
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")


async def main():
    # Agent Platformの初期化
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION
    )

    # エージェントの取得
    agent_engine = agent_engines.get(AGENT_ENGINE_ID)

    # セッションの作成
    user_id = str(uuid.uuid4())
    session = agent_engine.create_session(user_id=user_id)
    print("セッションを開始しました。'exit' で終了します。\n")

    while True:
        # ユーザー入力を取得
        user_input = input("You: ").strip()

        if user_input.lower() in["exit", "quit", "q"]:
            print("セッションを終了します。")
            break

        if not user_input:
            continue

        # エージェントへの問い合わせ
        print("Agent: ", end="", flush=True)
        async for event in agent_engine.async_stream_query(
            user_id=user_id,
            session_id=session["id"],
            message=user_input,
        ):
            # 回答テキストのみを抽出
            if "content" in event and "parts" in event["content"]:
                for part in event["content"]["parts"]:
                    if "text" in part:
                        print(part["text"], end="", flush=True)
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
