# src/pipeline/delete_schedule.py
# パイプラインのスケジュール削除

import google.cloud.aiplatform as aip
from pipeline import project_id

PROJECT_REGION = "asia-northeast1"


def delete_schedule(schedule_name: str):
    """スケジュールを削除する"""

    pipeline_job_schedule = aip.PipelineJobSchedule.get(schedule_name)
    pipeline_job_schedule.delete()
    print(f"スケジュールを削除しました: {schedule_name}")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # 環境変数からスケジュールIDを取得（または直接指定）
    SCHEDULE_ID = os.getenv("SCHEDULE_ID", "xxxxxxxxxx")

    aip.init(
        project=project_id,
        location=PROJECT_REGION,
    )

    # フルリソース名を構築
    schedule_name = f"projects/{project_id}/locations/{PROJECT_REGION}/schedules/{SCHEDULE_ID}"

    delete_schedule(schedule_name=schedule_name)
