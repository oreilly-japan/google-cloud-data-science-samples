# Agent Platform Inferenceを用いた予測基盤の構築（サンプルコード）

第Ⅰ部 9章のサンプルコードです。8章で作成したモデル・リソースを前提としています。
各設定値や手順の詳細は書籍 9章を参照してください。

## セットアップ

```zsh
# 依存パッケージのインストール
uv sync

# 環境変数の設定（.env.template をコピーして値を設定）
cp .env.template .env
```

## 実行手順（概要）

コマンドはすべてこのディレクトリ（プロジェクトルート）から実行します。

```zsh
# 予測用データの準備
uv run python src/prepare_data.py

# バッチ予測の実行と結果確認
uv run python src/batch_prediction.py
uv run python src/check_batch_results.py

# 学習からデプロイまでのパイプライン（src/pipeline_config/ に YAML が生成される）
mkdir -p src/pipeline_config
uv run python src/pipeline/pipeline.py
uv run python src/pipeline/run_pipeline.py

# オンライン予測
uv run python src/online_prediction.py

# リソースの削除（課金を止める）
uv run python src/cleanup/delete_endpoint.py
uv run python src/cleanup/delete_model.py
uv run python src/cleanup/delete_batch_prediction_job.py
uv run python src/cleanup/delete_gcs_data.py
```

`src/pipeline_config/` の YAML は実行時に生成されるため、リポジトリには含まれていません。

補足スクリプト（書籍未掲載）: `src/cleanup/delete_training_resources.py` — 8 章で作成した学習リソース（実験用モデル・GCS の学習成果物・Vertex AI Experiments の実験・パイプライン実行アーティファクト・Artifact Registry のイメージ）をまとめて削除します。
