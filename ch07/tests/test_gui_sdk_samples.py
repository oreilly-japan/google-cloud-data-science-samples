"""Offline request and guard tests for the Chapter 7 GUI-equivalent SDK samples."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CH07 = Path(__file__).resolve().parents[1]
for directory in (
    CH07 / "section_02_dataset_preparation",
    CH07 / "section_03_automl",
    CH07 / "section_06_scheduler",
    CH07 / "section_08_advanced_image",
):
    sys.path.insert(0, str(directory))

import batch_prediction  # noqa: E402
import create_dataset  # noqa: E402
import create_scheduler  # noqa: E402
import create_vertex_dataset  # noqa: E402
import train_automl  # noqa: E402
import train_automl_vision  # noqa: E402

PROJECT = "example-project-123"
LOCATION = "us-central1"
DATASET = f"projects/{PROJECT}/locations/{LOCATION}/datasets/123456789"
MODEL = f"projects/{PROJECT}/locations/{LOCATION}/models/987654321"
SERVICE_ACCOUNT = f"runner@{PROJECT}.iam.gserviceaccount.com"


def never_create_client():
    pytest.fail("dry-run must not construct a client")


def test_tabular_dataset_request_and_guards():
    request = create_vertex_dataset.build_request(
        PROJECT, LOCATION, "NYC taxi dataset", f"bq://{PROJECT}.nyc_taxi.tip_prediction_2022"
    )
    assert request.parent == f"projects/{PROJECT}/locations/{LOCATION}"
    assert request.import_config()["bigquery_source"]["input_uri"].endswith("tip_prediction_2022")
    create_vertex_dataset.execute_request(
        request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        create_vertex_dataset.execute_request(request, dry_run=False, allow_billable=False)

    seen = []

    class FakeClient:
        def create_and_import(self, candidate):
            seen.append(candidate)
            return DATASET

    assert (
        create_vertex_dataset.execute_request(
            request, dry_run=False, allow_billable=True, client_factory=lambda: FakeClient()
        )
        == DATASET
    )
    assert seen == [request]
    with pytest.raises(ValueError, match="BigQuery table"):
        create_vertex_dataset.build_request(PROJECT, LOCATION, "dataset", "bq://bad.table")


def test_tabular_automl_request_has_target_budget_and_no_client_on_dry_run():
    request = train_automl.build_request(
        PROJECT, LOCATION, DATASET, "tip_amount", 1000, "taxi model", "taxi automl training"
    )
    assert request.target_column == "tip_amount"
    assert request.budget_milli_node_hours == 1000
    train_automl.execute_request(
        request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        train_automl.execute_request(request, dry_run=False, allow_billable=False)

    seen = []

    class FakeClient:
        def start_training(self, candidate):
            seen.append(candidate)
            return f"projects/{PROJECT}/locations/{LOCATION}/trainingPipelines/111"

    assert (
        train_automl.execute_request(
            request, dry_run=False, allow_billable=True, client_factory=lambda: FakeClient()
        )
        == f"projects/{PROJECT}/locations/{LOCATION}/trainingPipelines/111"
    )
    assert seen == [request]
    assert (seen[0].project_id, seen[0].location) == (PROJECT, LOCATION)
    assert (seen[0].target_column, seen[0].budget_milli_node_hours) == ("tip_amount", 1000)
    assert (seen[0].model_display_name, seen[0].training_job_display_name) == (
        "taxi model",
        "taxi automl training",
    )
    with pytest.raises(ValueError, match="budget"):
        train_automl.build_request(PROJECT, LOCATION, DATASET, "tip_amount", 999, "model", "job")
    with pytest.raises(ValueError, match="Dataset resource"):
        train_automl.build_request(
            PROJECT,
            LOCATION,
            "projects/other/locations/us-central1/datasets/1",
            "tip_amount",
            1000,
            "m",
            "j",
        )


def test_batch_prediction_request_explicit_input_output_and_billable_guard():
    request = batch_prediction.build_request(
        PROJECT,
        LOCATION,
        MODEL,
        f"bq://{PROJECT}.nyc_taxi.tip_prediction_2022_test",
        f"bq://{PROJECT}.nyc_taxi",
        "taxi batch prediction",
        "n1-standard-4",
    )
    assert request.input_bigquery_table.endswith("tip_prediction_2022_test")
    assert request.output_bigquery_dataset == f"bq://{PROJECT}.nyc_taxi"
    batch_prediction.execute_request(
        request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        batch_prediction.execute_request(request, dry_run=False, allow_billable=False)

    seen = []

    class FakeClient:
        def start(self, candidate):
            seen.append(candidate)
            return f"projects/{PROJECT}/locations/{LOCATION}/batchPredictionJobs/222"

    assert (
        batch_prediction.execute_request(
            request, dry_run=False, allow_billable=True, client_factory=lambda: FakeClient()
        )
        == f"projects/{PROJECT}/locations/{LOCATION}/batchPredictionJobs/222"
    )
    assert seen == [request]
    assert (seen[0].project_id, seen[0].location, seen[0].model_name) == (PROJECT, LOCATION, MODEL)
    assert seen[0].input_bigquery_table.endswith("tip_prediction_2022_test")
    assert seen[0].output_bigquery_dataset == f"bq://{PROJECT}.nyc_taxi"
    assert seen[0].display_name == "taxi batch prediction"
    with pytest.raises(ValueError, match="output dataset"):
        batch_prediction.build_request(
            PROJECT,
            LOCATION,
            MODEL,
            f"bq://{PROJECT}.nyc_taxi.input",
            f"bq://{PROJECT}.nyc_taxi.table",
            "batch",
            "n1-standard-4",
        )


def test_scheduler_request_has_parent_endpoint_service_account_and_dry_run():
    body = {"displayName": "weekly trainer", "jobSpec": {"serviceAccount": SERVICE_ACCOUNT}}
    request = create_scheduler.build_request(
        PROJECT, LOCATION, "weekly-trainer", "0 2 * * 1", "Asia/Tokyo", SERVICE_ACCOUNT, body
    )
    assert request.parent == f"projects/{PROJECT}/locations/{LOCATION}"
    assert request.target_uri.endswith(f"projects/{PROJECT}/locations/{LOCATION}/customJobs")
    assert request.oauth_service_account == SERVICE_ACCOUNT
    create_scheduler.execute_request(
        request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        create_scheduler.execute_request(request, dry_run=False, allow_billable=False)

    seen = []

    class FakeClient:
        def create(self, candidate):
            seen.append(candidate)
            return candidate.name

    assert (
        create_scheduler.execute_request(
            request, dry_run=False, allow_billable=True, client_factory=lambda: FakeClient()
        )
        == f"projects/{PROJECT}/locations/{LOCATION}/jobs/weekly-trainer"
    )
    assert seen == [request]
    assert seen[0].custom_job_body["displayName"] == "weekly trainer"
    assert seen[0].custom_job_body["jobSpec"] == {"serviceAccount": SERVICE_ACCOUNT}
    with pytest.raises(ValueError, match="one-line cron"):
        create_scheduler.build_request(
            PROJECT,
            LOCATION,
            "weekly-trainer",
            "0 2 * * 1\nnext",
            "Asia/Tokyo",
            SERVICE_ACCOUNT,
            body,
        )


def test_image_dataset_and_automl_requests_have_manifest_dataset_and_budget_guards():
    dataset_request = create_dataset.build_request(
        PROJECT, LOCATION, "flowers", "gs://example-flowers-bucket/manifests/flowers_import.csv"
    )
    assert dataset_request.manifest_uri.endswith("flowers_import.csv")
    create_dataset.execute_request(
        dataset_request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        create_dataset.execute_request(dataset_request, dry_run=False, allow_billable=False)

    dataset_seen = []

    class FakeDatasetClient:
        def create(self, candidate):
            dataset_seen.append(candidate)
            return DATASET

    assert (
        create_dataset.execute_request(
            dataset_request,
            dry_run=False,
            allow_billable=True,
            client_factory=lambda: FakeDatasetClient(),
        )
        == DATASET
    )
    assert dataset_seen == [dataset_request]
    assert (dataset_seen[0].project_id, dataset_seen[0].location) == (PROJECT, LOCATION)
    assert dataset_seen[0].display_name == "flowers"
    with pytest.raises(ValueError, match="non-wildcard"):
        create_dataset.build_request(
            PROJECT, LOCATION, "flowers", "gs://example-bucket/images/*.csv"
        )

    request = train_automl_vision.build_request(
        PROJECT, LOCATION, DATASET, "flowers model", "flowers training", 8000
    )
    assert request.budget_milli_node_hours == 8000
    train_automl_vision.execute_request(
        request, dry_run=True, allow_billable=False, client_factory=never_create_client
    )
    with pytest.raises(PermissionError):
        train_automl_vision.execute_request(request, dry_run=False, allow_billable=False)

    training_seen = []

    class FakeTrainingClient:
        def start_training(self, candidate):
            training_seen.append(candidate)
            return f"projects/{PROJECT}/locations/{LOCATION}/trainingPipelines/333"

    assert (
        train_automl_vision.execute_request(
            request,
            dry_run=False,
            allow_billable=True,
            client_factory=lambda: FakeTrainingClient(),
        )
        == f"projects/{PROJECT}/locations/{LOCATION}/trainingPipelines/333"
    )
    assert training_seen == [request]
    assert (training_seen[0].dataset_name, training_seen[0].budget_milli_node_hours) == (
        DATASET,
        8000,
    )
    assert (training_seen[0].model_display_name, training_seen[0].training_job_display_name) == (
        "flowers model",
        "flowers training",
    )
    with pytest.raises(ValueError, match="8000"):
        train_automl_vision.build_request(
            PROJECT, LOCATION, DATASET, "flowers model", "flowers training", 7999
        )
