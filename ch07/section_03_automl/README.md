# 7.3 表形式 AutoML

書籍でGoogle Cloudコンソールから行うAgent Platform AutoMLとBatch Inferenceのバッチ予測（`BatchPredictionJob`）を、Python SDKで実行する参考例です。設定の意味と操作の背景は書籍7.3節を参照してください。

| ファイル | 役割 |
| --- | --- |
| `train_automl.py` | 既存 Dataset から回帰 AutoML 学習を開始 |
| `batch_prediction.py` | BigQuery table を入力にバッチ予測を開始 |
| `inspect_batch_prediction.sql` | BigQuery の予測出力を確認する SQL |

`dataset-name`と`model-name`は完全なAgent Platform resource name、BigQuery入出力は`bq://` URIを指定します。学習の入力はDataset、出力はModel resource、バッチ予測の入力はBigQuery table、出力先はBigQuery datasetです。

```bash
uv run python section_03_automl/train_automl.py \
  --project-id your-project-id --location us-central1 \
  --dataset-name projects/your-project-id/locations/us-central1/datasets/123456789 \
  --target-column tip_amount --budget-milli-node-hours 1000 \
  --model-display-name nyc-taxi-model --training-job-display-name nyc-taxi-train --dry-run

uv run python section_03_automl/batch_prediction.py \
  --project-id your-project-id --location us-central1 \
  --model-name projects/your-project-id/locations/us-central1/models/987654321 \
  --input-bigquery-table bq://your-project-id.nyc_taxi.tip_prediction_2022_test \
  --output-bigquery-dataset bq://your-project-id.nyc_taxi \
  --display-name nyc-taxi-batch --dry-run
```

`--dry-run`ではGoogle Cloud APIを呼び出さずに、学習またはバッチ予測の実行内容を確認できます。Google Cloud上で実行する場合は、それぞれのコマンドの`--dry-run`を`--allow-billable`に置き換えます。

Google Cloud上でAutoML学習やバッチ予測を実行するには、Google Cloudへの認証と、対象プロジェクトで各操作を行う権限が必要です。学習に使用するリソースや実行時間、バッチ予測の処理量に応じて料金が発生します。
