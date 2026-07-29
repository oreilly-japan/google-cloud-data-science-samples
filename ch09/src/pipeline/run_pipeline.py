# src/pipeline/run_pipeline.py
import os
import time

from dotenv import load_dotenv
from google.cloud import aiplatform

load_dotenv()

project_id = os.getenv("PROJECT_ID")
pipeline_root_path = os.getenv("PIPELINE_ROOT")
project_region = "asia-northeast1"

# Agent Platform の初期化
aiplatform.init(
    project=project_id,
    location=project_region,
)

# パイプライン設定
pipeline_yaml_path = "src/pipeline_config/nyc_taxi_tip_training_and_deployment_pipeline.yaml"
model_display_name = "nyc-taxi-tip-xgboost-model"
endpoint_display_name = "nyc-taxi-tip-endpoint"
serving_container_uri = "asia-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.2-1:latest"

# バケット名（PIPELINE_ROOTから抽出）
bucket_name = pipeline_root_path.replace("gs://", "").rstrip("/").split("/")[0]

# パイプラインジョブの作成
job = aiplatform.PipelineJob(
    display_name="nyc-taxi-tip-training-and-deployment",
    template_path=pipeline_yaml_path,
    pipeline_root=pipeline_root_path,
    parameter_values={
        "project_id": project_id,
        "region": project_region,
        "model_display_name": model_display_name,
        "endpoint_display_name": endpoint_display_name,
        "serving_container_uri": serving_container_uri,
        "bucket_name": bucket_name,
        "data_path": "data/nyc-taxi-tip-2022/taxi-*.csv",
        "learning_rate": 0.1,
        "max_depth": 6,
        "n_estimators": 100,
        "deploy_machine_type": "n1-standard-2",
        "min_replica_count": 1,
        "max_replica_count": 1,
    },
    enable_caching=False,
)


if __name__ == "__main__":
    job.submit()

    # パイプラインの実行状態を監視
    while True:
        job._sync_gca_resource()
        state = job.state
        print(f"Pipeline state: {state.name}")

        if state in [
            aiplatform.gapic.PipelineState.PIPELINE_STATE_SUCCEEDED,
            aiplatform.gapic.PipelineState.PIPELINE_STATE_FAILED,
            aiplatform.gapic.PipelineState.PIPELINE_STATE_CANCELLED,
        ]:
            if state == aiplatform.gapic.PipelineState.PIPELINE_STATE_FAILED:
                print("Pipeline run failed")
            elif state == aiplatform.gapic.PipelineState.PIPELINE_STATE_SUCCEEDED:
                print("Pipeline run completed successfully")
            break

        time.sleep(60)
