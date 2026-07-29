-- Chapter 7 / section 7.2: export the training table as CSV shards.
--
-- Replace {{PROJECT_ID}}, {{DATASET_ID}}, {{TABLE_ID}}, and {{BUCKET_NAME}}.
-- overwrite=true replaces objects under this prefix.
EXPORT DATA OPTIONS(
  uri = 'gs://{{BUCKET_NAME}}/data/nyc-taxi-tip-2022/taxi-*.csv',
  format = 'CSV',
  overwrite = true,
  header = true,
  field_delimiter = ','
) AS
SELECT * FROM `{{PROJECT_ID}}.{{DATASET_ID}}.{{TABLE_ID}}`;
