# src/pipeline/run_experiment.py
import google.cloud.aiplatform as aip
from pipeline import (
    project_id,
    pipeline_root_path,
    project_region,
    model_display_name,
    serving_container_uri,
    YOUR_YAML_FILE_PATH,
)

EXPERIMENT_NAME = "xgboost-max-depth-experiment"

# PIPELINE_ROOTからバケット名を抽出（gs://bucket-name/path → bucket-name）
bucket_name = pipeline_root_path.replace("gs://", "").rstrip("/").split("/")[0]

# max_depthの値を変えて実験
max_depth_values = [3, 6, 9]

aip.init(project=project_id, location=project_region)

for max_depth in max_depth_values:
    job = aip.PipelineJob(
        display_name=f"xgboost-max-depth-{max_depth}",
        template_path=YOUR_YAML_FILE_PATH,
        pipeline_root=pipeline_root_path,
        parameter_values={
            "project_id": project_id,
            "region": project_region,
            "model_display_name": f"{model_display_name}-depth-{max_depth}",
            "serving_container_uri": serving_container_uri,
            "bucket_name": bucket_name,
            "data_path": "data/nyc-taxi-tip-2022/taxi-*.csv",
            "learning_rate": 0.1,
            "max_depth": max_depth,
            "n_estimators": 100,
        },
    )
    job.submit(experiment=EXPERIMENT_NAME)
    print(f"Submitted experiment with max_depth={max_depth}")
