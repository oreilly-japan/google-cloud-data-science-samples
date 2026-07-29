"""
Cloud Run function to trigger Agent Platform Batch Prediction Job.
Scheduled by Cloud Scheduler to run daily at 5:00 AM JST.

After the batch prediction job completes, it appends the results
to 'predicted_results' table for easy access and historical tracking.
"""
import functions_framework
from google.cloud import aiplatform
from google.cloud import bigquery
from datetime import datetime
import os


# Configuration - Set these via environment variables
PROJECT_ID = os.environ.get("PROJECT_ID")
REGION = os.environ.get("REGION")
MODEL_ID = os.environ.get("MODEL_ID")
INPUT_BQ_URI = os.environ.get("INPUT_BQ_URI")
OUTPUT_BQ_PREFIX = os.environ.get("OUTPUT_BQ_PREFIX")

# Dataset for predictions (extracted from OUTPUT_BQ_PREFIX)
# e.g., "bq://project.dataset" -> "project.dataset"
OUTPUT_DATASET = OUTPUT_BQ_PREFIX.replace("bq://", "")


def append_predicted_results():
    """
    Find the latest predictions_* table and append its contents to 'predicted_results'.
    Creates the table if it doesn't exist, otherwise inserts new rows.
    After appending, deletes the source predictions_* table.
    """
    client = bigquery.Client(project=PROJECT_ID)
    dataset_id = OUTPUT_DATASET.split(".")[-1]  # e.g., "uci_data"
    
    # Find the latest predictions table
    query = f"""
        SELECT table_name, creation_time
        FROM `{PROJECT_ID}.{dataset_id}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name LIKE 'predictions_%'
        ORDER BY creation_time DESC
        LIMIT 1
    """
    
    result = client.query(query).result()
    rows = list(result)
    
    if not rows:
        print("No predictions tables found yet. Skipping append.")
        return None
    
    latest_table = rows[0].table_name
    print(f"Found latest predictions table: {latest_table}")
    
    # Check if predicted_results table exists
    check_table_query = f"""
        SELECT COUNT(*) as cnt
        FROM `{PROJECT_ID}.{dataset_id}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name = 'predicted_results'
    """
    check_result = client.query(check_table_query).result()
    table_exists = list(check_result)[0].cnt > 0
    
    # Build query: CREATE TABLE if not exists, otherwise INSERT
    # Include job_run_at timestamp to identify when the job was executed
    target_table = f"`{PROJECT_ID}.{dataset_id}.predicted_results`"
    prefix = f"INSERT INTO {target_table}" if table_exists else f"CREATE TABLE {target_table} AS"
    
    query = f"""
        {prefix}
        SELECT
            customer_id,
            prediction_date,
            CURRENT_TIMESTAMP() AS job_run_at,
            GREATEST(0, predicted_target.value) AS pred,
            predicted_target.value AS pred_raw,
            predicted_target.lower_bound AS pred_lower,
            predicted_target.upper_bound AS pred_upper
        FROM
            `{PROJECT_ID}.{dataset_id}.{latest_table}`
    """
    client.query(query).result()
    action = "Appended to" if table_exists else "Created"
    print(f"{action} predicted_results from {latest_table}")
    
    # Delete the source predictions table after successful append
    source_table_ref = f"{PROJECT_ID}.{dataset_id}.{latest_table}"
    client.delete_table(source_table_ref)
    print(f"Deleted source table: {latest_table}")
    
    return latest_table


@functions_framework.http
def trigger_batch_prediction(request):
    """
    HTTP Cloud Function to trigger a Vertex AI Batch Prediction Job.

    Args:
        request: Flask request object (not used, but required for HTTP trigger)

    Returns:
        JSON response with job details
    """
    # Generate unique job name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize Vertex AI
    aiplatform.init(project=PROJECT_ID, location=REGION)

    # Get the model resource name
    model_resource_name = f"projects/{PROJECT_ID}/locations/{REGION}/models/{MODEL_ID}"

    print(f"Starting batch prediction job...")
    print(f"  Model: {model_resource_name}")
    print(f"  Input: {INPUT_BQ_URI}")
    print(f"  Output Dataset: {OUTPUT_BQ_PREFIX}")

    # sync=True: Wait for job completion before proceeding
    # Note: Batch prediction typically takes a few minutes
    job_display_name = f"scheduled-prediction-{timestamp}"
    model = aiplatform.Model(model_resource_name)
    batch_prediction_job = model.batch_predict(
        job_display_name=job_display_name,
        bigquery_source=INPUT_BQ_URI,
        bigquery_destination_prefix=OUTPUT_BQ_PREFIX,
        sync=True,
    )

    print(f"Batch prediction job completed: {batch_prediction_job.resource_name}")

    # Append the current job's results to predicted_results table
    copied_table = None
    try:
        copied_table = append_predicted_results()
    except Exception as e:
        print(f"Warning: Failed to copy predicted results: {e}")

    response = {
        "status": "submitted",
        "job_name": batch_prediction_job.display_name,
        "job_resource_name": batch_prediction_job.resource_name,
        "input_uri": INPUT_BQ_URI,
        "output_dataset": OUTPUT_BQ_PREFIX,
        "copied_to_latest_from": copied_table,
        "timestamp": timestamp,
    }

    return response
