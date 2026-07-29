# 7.2 データ準備

BigQueryの作成・エクスポートSQLと、表形式Agent Platform DatasetのSDK例です。書籍のGoogle Cloudコンソール操作に対応するコード例であり、操作の背景は書籍7.2節を参照してください。

| ファイル | 役割 |
| --- | --- |
| `create_bigquery_table.sql` | 学習用 BigQuery テーブルを作成するテンプレート |
| `export_to_gcs.sql` | CSV を Cloud Storage にエクスポートするテンプレート |
| `data_prepare.py` | SQL の値をローカルで置換して表示 |
| `create_vertex_dataset.py` | BigQuery テーブルから表形式 Dataset を作成 |

`PROJECT_ID`、BigQuery dataset/table、バケット名、Agent Platformのリージョンを指定します。SQLの入力と出力はテンプレート内のBigQuery tableとGCS prefixです。

```bash
uv run python section_02_dataset_preparation/data_prepare.py render create \
  --project-id your-project-id --dataset-id nyc_taxi --table-id tip_prediction_2022

uv run python section_02_dataset_preparation/data_prepare.py render export \
  --project-id your-project-id --dataset-id nyc_taxi --table-id tip_prediction_2022 \
  --bucket-name your-bucket-name

uv run python section_02_dataset_preparation/create_vertex_dataset.py \
  --project-id your-project-id --location us-central1 --display-name nyc-taxi \
  --bigquery-source bq://your-project-id.nyc_taxi.tip_prediction_2022 --dry-run
```

`data_prepare.py render`と`--dry-run`はローカルで実行され、Google Cloud APIを呼び出しません。

Google Cloud上でDatasetを作成する場合は、上のコマンドの`--dry-run`を`--allow-billable`に置き換えます。実行には、Google Cloudへの認証と、対象プロジェクトでDatasetを作成する権限が必要です。データの保存や後続の学習処理には料金が発生する場合があります。
