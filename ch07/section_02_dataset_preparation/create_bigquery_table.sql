-- Chapter 7 / section 7.2: create the NYC Taxi training table.
--
-- Replace {{PROJECT_ID}}, {{DATASET_ID}}, and {{TABLE_ID}}. This statement
-- replaces the named table, so use a dedicated validation dataset/table.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.{{TABLE_ID}}` AS (
  SELECT
    pickup_datetime,
    passenger_count,
    trip_distance,
    CAST(payment_type AS STRING) AS payment_type,
    EXTRACT(DAYOFWEEK FROM pickup_datetime) AS day_of_week,
    EXTRACT(HOUR FROM pickup_datetime) AS hour_of_day,
    tip_amount
  FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
  TABLESAMPLE SYSTEM (10 PERCENT)
  WHERE tip_amount >= 0
    AND trip_distance > 0
    AND passenger_count > 0
    AND fare_amount > 0
);
