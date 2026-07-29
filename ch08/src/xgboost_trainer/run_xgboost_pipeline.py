# run_xgboost_pipeline.py
import time
import google.cloud.aiplatform as aip
from xgboost_pipeline import (
    project_id,
    pipeline_root,
    project_region,
    pipeline_name,
    model_display_name,
    serving_container_uri,
    bucket_name,
    pipeline_yaml_path,
)

aip.init(project=project_id, location=project_region)

job = aip.PipelineJob(
    display_name=pipeline_name,
    template_path=pipeline_yaml_path,
    pipeline_root=pipeline_root,
    parameter_values={
        "project_id": project_id,
        "region": project_region,
        "model_display_name": model_display_name,
        "serving_container_uri": serving_container_uri,
        "bucket_name": bucket_name,
        "data_path": "data/nyc-taxi-tip-2022/taxi-*.csv",
        "learning_rate": 0.1,
        "max_depth": 6,
        "n_estimators": 100,
    },
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
        break
    time.sleep(60)

if state == aip.gapic.PipelineState.PIPELINE_STATE_SUCCEEDED:
    print("Pipeline run completed successfully")
else:
    print(f"Pipeline run ended with state: {state.name}")
