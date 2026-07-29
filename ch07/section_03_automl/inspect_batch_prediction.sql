-- Chapter 7 / section 7.3, optional batch prediction check.
-- Replace {{PROJECT_ID}}, {{DATASET_ID}}, and {{PREDICTIONS_TABLE}}.
-- The prediction table name is created by the Agent Platform batch job and is
-- usually named predictions_*. Confirm its exact name in the BigQuery console.
SELECT
  *
FROM `{{PROJECT_ID}}.{{DATASET_ID}}.{{PREDICTIONS_TABLE}}`
LIMIT 20;
