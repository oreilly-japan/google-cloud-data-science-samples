# 7.6 Scheduler

Custom Training用のAgent Platform Custom Job本文をJSONで生成し、その本文を対象にCloud Scheduler HTTP Jobを作成する例です。書籍でGoogle Cloudコンソールから行う操作をコード化した参考例です。背景と設定の意味は書籍7.6節を参照してください。

| ファイル | 役割 |
| --- | --- |
| `scheduler-job-body.json` | Custom Job 本文のテンプレート |
| `scheduler_validate.py` | テンプレートを JSON として生成・検証 |
| `create_scheduler.py` | Cloud Scheduler Job を作成 |

プロジェクト、リージョン、実行イメージ、バケット、実行サービスアカウント、Scheduler job ID、cron、タイムゾーンを指定します。入力は生成済みの Custom Job JSON、出力は Scheduler Job resource name です。

```bash
uv run python section_06_scheduler/scheduler_validate.py \
  --set JOB_DISPLAY_NAME=nyc-taxi-weekly \
  --set IMAGE_URI=us-docker.pkg.dev/your-project-id/repo/trainer:latest \
  --set BUCKET_NAME=your-bucket-name \
  --set RUNTIME_SERVICE_ACCOUNT=your-service-account@your-project-id.iam.gserviceaccount.com \
  --set RUN_ID=20260729-ab12 > section_06_scheduler/scheduler-job-body.rendered.json

uv run python section_06_scheduler/create_scheduler.py \
  --project-id your-project-id --location us-central1 --job-id nyc-taxi-weekly \
  --schedule '0 2 * * 1' --time-zone Asia/Tokyo \
  --oauth-service-account your-service-account@your-project-id.iam.gserviceaccount.com \
  --body-json section_06_scheduler/scheduler-job-body.rendered.json --dry-run
```

`scheduler_validate.py`によるJSONの生成・検証と`--dry-run`はローカルで実行され、Google Cloud APIを呼び出しません。

Google Cloud上でScheduler Jobを作成する場合は、上のコマンドの`--dry-run`を`--allow-billable`に置き換えます。実行には、Google Cloudへの認証と、対象プロジェクトでScheduler Jobを作成する権限が必要です。また、指定したサービスアカウントを使用する権限も必要です。Scheduler Jobと呼び出し先のサービスの利用に応じて料金が発生する場合があります。
