# src/cleanup/delete_batch_prediction_job.py
# バッチ予測ジョブの削除

from google.cloud import aiplatform


def delete_batch_prediction_job(
    project_id: str,
    location: str,
    job_display_name: str
):
    """バッチ予測ジョブを削除する"""

    aiplatform.init(project=project_id, location=location)

    jobs = aiplatform.BatchPredictionJob.list(
        filter=f'display_name="{job_display_name}"'
    )

    for job in jobs:
        job.delete()
        print(f"バッチ予測ジョブ '{job.display_name}' を削除しました")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    PROJECT_REGION = "asia-northeast1"
    JOB_DISPLAY_NAME = "nyc-taxi-tip-batch-prediction"

    delete_batch_prediction_job(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        job_display_name=JOB_DISPLAY_NAME
    )
