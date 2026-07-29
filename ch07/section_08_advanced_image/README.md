# 7.8 画像分類

花画像の import manifest、Image Dataset、Agent Platform AutoML による画像分類学習のサンプルです。画像データは含みません。書籍で Google Cloud コンソールで行う操作をコード化した参考例であり、データ取得と操作の背景は書籍7.8節を参照してください。

| ファイル | 役割 |
| --- | --- |
| `data_flowers_manifest.py` | ローカル画像から import CSV を生成 |
| `create_dataset.py` | GCS manifest から Image Dataset を作成 |
| `train_automl_vision.py` | Image Dataset から分類 AutoML 学習を開始 |

manifest の入力は `daisy`、`dandelion`、`roses`、`sunflowers`、`tulips` の各画像ディレクトリ、出力は GCS 上の画像を参照する CSV です。生成した CSV と参照画像を指定バケットへ配置し、その CSV URI を Dataset 作成の `--manifest-uri` に指定します。学習には完全な Dataset resource name を指定します。以下のコマンドは、この章のディレクトリから実行します。

まず、対象ファイルと出力予定を確認します。

```bash
uv run python section_08_advanced_image/data_flowers_manifest.py \
  --source-dir flower_photos --bucket-name your-bucket-name \
  --output section_08_advanced_image/flowers_import.csv --dry-run
```

確認後、`--dry-run` を外して manifest を生成します。

```bash
uv run python section_08_advanced_image/data_flowers_manifest.py \
  --source-dir flower_photos --bucket-name your-bucket-name \
  --output section_08_advanced_image/flowers_import.csv

uv run python section_08_advanced_image/create_dataset.py \
  --project-id your-project-id --location us-central1 --display-name flowers \
  --manifest-uri gs://your-bucket-name/manifests/flowers_import.csv --dry-run

uv run python section_08_advanced_image/train_automl_vision.py \
  --project-id your-project-id --location us-central1 \
  --dataset-name projects/your-project-id/locations/us-central1/datasets/123456789 \
  --model-display-name flowers-model --training-job-display-name flowers-train \
  --budget-milli-node-hours 8000 --dry-run
```

manifestの確認と生成はローカルで実行され、Google Cloud APIを呼び出しません。Dataset作成と学習の`--dry-run`も、Google Cloud APIを呼び出さずに実行内容を確認します。

Google Cloud上でImage Datasetを作成する場合は、`create_dataset.py`の`--dry-run`を`--allow-billable`に置き換えます。実行には、Google Cloudへの認証と、対象プロジェクトでDatasetを作成する権限が必要です。データの保存や後続の学習処理には料金が発生する場合があります。

Google Cloud上でAutoML学習を実行する場合は、`train_automl_vision.py`の`--dry-run`を`--allow-billable`に置き換えます。実行には、Google Cloudへの認証と、対象プロジェクトで学習ジョブを作成する権限が必要です。学習に使用するリソースと実行時間に応じて料金が発生します。
