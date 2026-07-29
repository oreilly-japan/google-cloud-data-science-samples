# src/pipeline/create_schedule.py
# パイプラインのスケジュール作成

import google.cloud.aiplatform as aip
from pipeline import (
    project_id,
    pipeline_root_path,
    model_display_name,
    serving_container_uri,
    YOUR_YAML_FILE_PATH,
)

PROJECT_REGION = "asia-northeast1"
BUCKET_NAME = pipeline_root_path.replace("gs://", "").rstrip("/").split("/")[0]
SCHEDULE_DISPLAY_NAME = "HANDSON_SCHEDULE"
MAX_CONCURRENT_RUN_COUNT = 1
MAX_RUN_COUNT = 10


def create_schedule(cron: str = "0 2 * * *"):
    """パイプラインのスケジュールを作成する"""

    # 引数はrun_pipeline.pyと同様
    job = aip.PipelineJob(
        display_name="nyc-taxi-tip-prediction-pipeline",
        template_path=YOUR_YAML_FILE_PATH,
        pipeline_root=pipeline_root_path,
        parameter_values={
            "project_id": project_id,
            "region": PROJECT_REGION,
            "model_display_name": model_display_name,
            "serving_container_uri": serving_container_uri,
            "bucket_name": BUCKET_NAME,
            "data_path": "data/nyc-taxi-tip-2022/taxi-*.csv",
            "learning_rate": 0.1,
            "max_depth": 6,
            "n_estimators": 100,
        },
        enable_caching=False,
    )

    pipeline_job_schedule = aip.PipelineJobSchedule(
        pipeline_job=job,
        display_name=SCHEDULE_DISPLAY_NAME
    )

    pipeline_job_schedule.create(
        cron=cron,
        max_concurrent_run_count=MAX_CONCURRENT_RUN_COUNT,
        max_run_count=MAX_RUN_COUNT,
    )

    return pipeline_job_schedule


if __name__ == "__main__":
    aip.init(project=project_id, location=PROJECT_REGION)
    print("スケジュールを作成...")
    create_schedule(cron="0 2 * * *")
