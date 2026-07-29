# gcloud-release-agent/gcloud_release_agent/agent.py
import os
from datetime import datetime

from dotenv import load_dotenv
import google.auth
from google.adk.agents import LlmAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode

# .envファイルから環境変数を読み込み
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
TODAY = datetime.now().strftime("%Y-%m-%d")

# 読み取り専用のユースケースでは、明示的に書き込みを禁止することで安全性を高める
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# Application Default Credentials (ADC) を取得
credentials, _ = google.auth.default()

# 認証設定
credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# BigQueryToolsetの作成
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config,
    bigquery_tool_config=tool_config
)

# --- エージェント定義 ---
root_agent = LlmAgent(
    name="gcloud_docs_agent",
    model="gemini-2.5-pro", # 使用するモデルバージョン
    description="Google Cloudのドキュメントやリリースノートを検索して質問に回答するエージェント",
    instruction=f"""あなたはGoogle Cloudの専門家アシスタントです。知識豊富なエンジニアとして振る舞ってください。

今日の日付: {TODAY}

ユーザーからの質問に対して、以下のツールを適切に使い分けて回答してください。

1. google_search: Google Cloudの公式ドキュメントや技術情報を検索する際に使用します。
    サービス名称の言い換えや最新のベストプラクティスを調べる場合に使用してください。

2. BigQueryツール: Google Cloudサービスの最新リリースノートを取得する際に使用します。
    リリースノートは `bigquery-public-data.google_cloud_release_notes.release_notes` テーブルに格納されています。
    execute_sqlツールを使用して、以下のようなクエリでリリースノートを取得できます：
    BigQueryジョブはプロジェクトID `{PROJECT_ID}` で実行します。

    SELECT published_at, product_name, description, release_note_type
    FROM `bigquery-public-data.google_cloud_release_notes.release_notes`
    WHERE LOWER(product_name) LIKE LOWER('%製品名%')
    ORDER BY published_at DESC
    LIMIT 5

回答ガイドライン：

- 情報の正確性を最優先してください。不確実な場合は推測せず正直に伝えてください。
- 技術的な内容は、可能な限り具体的なコード例や設定例を含めてください。
- 引用元となる公式ドキュメントのURLがあれば必ず提示してください。
- 出力は日本語で行ってください。
- リリースノート情報はMarkdownの表形式で整理して提示してください。
""",
    tools=[GoogleSearchTool(bypass_multi_tools_limit=True), bigquery_toolset]
)
