# 機械学習パイプラインによるMLOpsの実現（サンプルコード）

第Ⅰ部 8章のサンプルコードです。
各設定値や手順の詳細は書籍 8章を参照してください。

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
# パイプラインのコンパイル（src/pipeline_config/ に YAML が生成される）
mkdir -p src/pipeline_config
uv run python src/pipeline/pipeline.py

# パイプラインの実行
uv run python src/pipeline/run_pipeline.py

# Agent Platform Experiments による実験管理
uv run python src/pipeline/run_experiment.py

# パイプラインのスケジュール実行
uv run python src/pipeline/create_schedule.py
```

コンテナ化された Python コンポーネント（8.6節）は `src/xgboost_trainer/` で作業します。

```zsh
cd src/xgboost_trainer
uv run kfp component build src/ --component-filepattern xgboost_trainer.py --push-image

# パイプラインのコンパイルと実行（src/pipeline_config/ に YAML が生成される）
mkdir -p src/pipeline_config
uv run python xgboost_pipeline.py
uv run python run_xgboost_pipeline.py
```

パイプラインのコンパイルで生成される YAML や `kfp component build` の生成物（Dockerfile など）は実行時に生成されるため、リポジトリには含まれていません。

補足スクリプト（書籍未掲載）: `src/pipeline/delete_schedule.py` — 作成したスケジュールを削除します（書籍ではコンソールからの削除を案内しています）。`.env` の `SCHEDULE_ID` に対象のスケジュール ID を設定して実行してください。
