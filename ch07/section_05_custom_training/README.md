# 7.5 Custom Training

書籍7.5節の Custom Training サンプルです。`task.py` は CPU、`dist_task.py` は分散、`hpt_task.py` と `hptuning_config.yaml` は HPT、`gpu/dl_task.py` と `gpu/Dockerfile` は GPU の例です。`submit_custom_training.py` は送信コマンドを作成します。

必須値は project ID、リージョン、バケット名、ジョブ表示名、実行イメージです。入力は Cloud Storage の CSV、出力は指定した Cloud Storage のモデル prefix です。

```bash
uv run python section_05_custom_training/submit_custom_training.py \
  --mode cpu --project-id your-project-id --region us-central1 \
  --display-name nyc-taxi-cpu --bucket-name your-bucket-name \
  --package-path section_05_custom_training \
  --image-uri REGION-docker.pkg.dev/vertex-ai/training/EXECUTOR_IMAGE:TAG --dry-run
```

`--dry-run`ではGoogle Cloud APIを呼び出さずに、送信予定のコマンドをローカルで確認できます。

`--mode` は `cpu`、`distributed`、`hpt`、`gpu` から選びます。分散は `--workers` を追加します。以下の HPT コマンドは、この章のディレクトリから実行します。

まず、テンプレートの値を置換した実行用 YAML をローカルで生成します。この処理はGoogle Cloud APIを呼び出しません。

```bash
uv run python section_05_custom_training/submit_custom_training.py \
  --mode hpt --project-id your-project-id --region us-central1 \
  --display-name nyc-taxi-hpt --bucket-name your-bucket-name \
  --image-uri REGION-docker.pkg.dev/PROJECT/REPOSITORY/hpt-trainer:TAG \
  --render-hpt-config section_05_custom_training/hptuning_config.rendered.yaml
```

生成した YAML を指定し、最初は dry-run で内容を確認します。

```bash
uv run python section_05_custom_training/submit_custom_training.py \
  --mode hpt --project-id your-project-id --region us-central1 \
  --display-name nyc-taxi-hpt --bucket-name your-bucket-name \
  --image-uri REGION-docker.pkg.dev/PROJECT/REPOSITORY/hpt-trainer:TAG \
  --hpt-config-path section_05_custom_training/hptuning_config.rendered.yaml \
  --max-trial-count 20 --parallel-trial-count 4 --dry-run
```

Google Cloud上でジョブを実行する場合は、上のコマンドの`--dry-run`を`--allow-billable`に置き換えます。実行には、Google Cloudへの認証と、対象プロジェクトでジョブを作成する権限が必要です。また、使用するリソースに応じて料金が発生します。詳しい手順は書籍7.5節を参照してください。
