# xgboost_pipeline.py
import os
from dotenv import load_dotenv
from kfp import compiler, dsl
from kfp.dsl import PipelineTask
from google_cloud_pipeline_components.v1.model import ModelUploadOp
from google_cloud_pipeline_components.types import artifact_types
from src.xgboost_trainer import train_xgboost

load_dotenv()

project_id = os.getenv("PROJECT_ID")
pipeline_root = os.getenv("PIPELINE_ROOT")
# PIPELINE_ROOTからバケット名を抽出（gs://bucket-name/path → bucket-name）
bucket_name = pipeline_root.replace("gs://", "").rstrip("/").split("/")[0]
project_region = "asia-northeast1"
pipeline_name = "nyc-taxi-tip-containerized-pipeline"
model_display_name = "nyc-taxi-tip-xgboost-model"

# 事前構築済み推論コンテナ（詳細は9章を参照）
serving_container_uri = (
    "asia-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.2-1:latest"
)

# パイプラインをコンパイルしたYAMLファイルのパス
pipeline_yaml_path = "src/pipeline_config/xgboost_containerized_pipeline.yaml"


@dsl.pipeline(name=pipeline_name, pipeline_root=pipeline_root)
def xgboost_pipeline(
    project_id: str,
    region: str,
    model_display_name: str,
    serving_container_uri: str,
    bucket_name: str,
    data_path: str = "data/nyc-taxi-tip-2022/taxi-*.csv",
    learning_rate: float = 0.1,
    max_depth: int = 6,
    n_estimators: int = 100,
):
    """XGBoost学習パイプライン"""
    # XGBoostモデルの学習
    training_task: PipelineTask = train_xgboost(
        bucket_name=bucket_name,
        data_path=data_path,
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators,
    ).set_memory_limit("32G").set_cpu_limit("4")

    # モデルをインポート
    import_model_task = dsl.importer(
        artifact_uri=training_task.outputs["model_uri"],
        artifact_class=artifact_types.UnmanagedContainerModel,
        metadata={
            "containerSpec": {
                "imageUri": serving_container_uri,
            },
        },
    )

    # モデルのアップロード
    ModelUploadOp(
        project=project_id,
        location=region,
        display_name=model_display_name,
        unmanaged_container_model=import_model_task.output,
    )


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=xgboost_pipeline,
        package_path=pipeline_yaml_path,
    )
