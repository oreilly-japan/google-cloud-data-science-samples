# Google ADKを用いたAIエージェント開発（サンプルコード）

第Ⅰ部 11章のサンプルコードです。
Google Cloud のドキュメント検索（Google Search）と BigQuery のリリースノート検索を行う AI エージェントを、ADK で開発して Agent Runtime にデプロイします。
各設定値や手順の詳細は書籍 11章を参照してください。

## セットアップ

```zsh
# 依存パッケージのインストール
uv sync

# 環境変数の設定（.env.template をコピーして値を設定）
cp gcloud_release_agent/.env.template gcloud_release_agent/.env
```

`AGENT_ENGINE_ID` はデプロイ後に出力される値を設定します。

## 実行手順（概要）

コマンドはすべてこのディレクトリ（プロジェクトルート）から実行します。

```zsh
# ローカルでのテスト（ADK Web）
uv run adk web

# ステージングバケットの作成（初回のみ）
export PROJECT_ID=$(gcloud config get-value project)
export BUCKET_NAME="${PROJECT_ID}-adk-staging"
gcloud storage buckets create gs://$BUCKET_NAME --project=$PROJECT_ID --location=us-central1

# Agent Runtime へのデプロイ
uv run adk deploy agent_engine \
    --project=$PROJECT_ID \
    --region=us-central1 \
    --staging_bucket=gs://$BUCKET_NAME \
    --display_name="Google Cloud Release Note Agent" \
    --trace_to_cloud \
    ./gcloud_release_agent

# デプロイしたエージェントとターミナルで対話
uv run python gcloud_release_agent/agent_engine_client_example.py
```

補足スクリプト（書籍未掲載）: `delete_agent_engine.py` — デプロイした Agent Runtime を削除します（課金を止めるため、ハンズオン終了後に実行してください）。
