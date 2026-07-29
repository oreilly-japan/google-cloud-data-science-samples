# src/pipeline/run_pipeline.py
import time
import google.cloud.aiplatform as aip
from pipeline import (
    project_id,
    pipeline_root_path,
    model_display_name,
    serving_container_uri,
    YOUR_YAML_FILE_PATH,
)

PROJECT_REGION = "asia-northeast1"
# PIPELINE_ROOTから バケット名を抽出（gs://bucket-name/ → bucket-name）
BUCKET_NAME = pipeline_root_path.replace("gs://", "").rstrip("/").split("/")[0]

aip.init(project=project_id, location=PROJECT_REGION)

# Prepare the pipeline job
job = aip.PipelineJob(
    display_name="nyc-taxi-tip-prediction-pipeline",
    template_path=YOUR_YAML_FILE_PATH,
    pipeline_root=pipeline_root_path,
    parameter_values={
        'project_id': project_id,
        'region': PROJECT_REGION,
        'model_display_name': model_display_name,
        'serving_container_uri': serving_container_uri,
        'bucket_name': BUCKET_NAME,
        'data_path': 'data/nyc-taxi-tip-2022/taxi-*.csv',
        'learning_rate': 0.1,
        'max_depth': 6,
        'n_estimators': 100,
    },
    enable_caching=False,
)

job.submit()

# パイプラインの実行状態を監視
while True:
    job._sync_gca_resource()
    state = job.state
    print(f"Pipeline state: {state.name}")

    if state in [
        aip.gapic.PipelineState.PIPELINE_STATE_SUCCEEDED,
        aip.gapic.PipelineState.PIPELINE_STATE_FAILED,
        aip.gapic.PipelineState.PIPELINE_STATE_CANCELLED,
    ]:
        if state == aip.gapic.PipelineState.PIPELINE_STATE_FAILED:
            print("Pipeline run failed")
        elif state == aip.gapic.PipelineState.PIPELINE_STATE_SUCCEEDED:
            print("Pipeline run completed successfully")
        break

    time.sleep(60)