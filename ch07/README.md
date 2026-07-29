# 第7章: Agent Platformによるモデル開発

書籍第7章の実行用サンプルです。本章ではGemini Enterprise Agent Platform（以下、Agent Platform）を使用します。各節の背景、Google Cloud コンソールでの操作、結果の解釈は書籍を参照してください。

## ディレクトリ

- `section_02_dataset_preparation/`: BigQuery のデータ準備と表形式 Dataset 作成例
- `section_03_automl/`: Agent Platform AutoML とBatch InferenceのSDK例
- `section_04_workbench/`: Agent Platform WorkbenchでのEDAとLightGBMのNotebook
- `section_05_custom_training/`: CPU、分散、HPT、GPU の Custom Training
- `section_06_scheduler/`: Custom Job の本文生成と Cloud Scheduler 作成例
- `section_08_advanced_image/`: 画像manifest、Dataset、Agent Platform AutoMLの例
- `cleanup_ch07.py`: 対象を限定した cleanup の実行計画

この章のディレクトリで依存関係を準備します。

```bash
uv sync --locked
```

各節の README に必須値、入力、出力、および実行コマンドを示します。SQL、YAML、JSON、manifestの生成と`--dry-run`はローカルで実行され、Google Cloud APIを呼び出しません。

Google Cloud上でDataset、学習ジョブ、バッチ予測、Scheduler Jobなどを作成するコマンドは、プロジェクト、リージョン、リソース名を引数で指定します。実行には、Google Cloudへの認証と、対象プロジェクトでこの操作を行う権限が必要です。また、使用するサービスやリソースに応じて料金が発生します。

不要な作成物を整理する場合は、まず次のコマンドで削除予定の対象をローカルに表示します。この時点ではGoogle Cloud上のリソースを削除しません。

```bash
uv run python cleanup_ch07.py --project-id your-project-id \
  --bucket-name your-bucket-name --prefix data/nyc-taxi-tip-2022/
```

削除を実行するには、Google Cloudへの認証と、対象リソースを削除する権限が必要です。`--execute`と確認オプションを指定する前に、表示されたバケットprefixまたはScheduler Jobが削除対象と一致することを確認してください。

詳細は書籍第7章を参照してください。
