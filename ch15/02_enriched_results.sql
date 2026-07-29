CREATE OR REPLACE VIEW `image_analysis.enriched_results` AS
SELECT
  p.uri,
  p.result,
  p.parsed_json,
  s.object_id,
  s.title,
  s.department,
  s.artist_display_name,
  s.artist_nationality,
  TRIM(REGEXP_REPLACE(SPLIT(culture, ' (')[OFFSET(0)], r'(?i)(Western|Eastern|North(ern)?|Central|Upper|probably)|,.*', '')) AS culture,
  s.object_begin_date,
  s.object_end_date,
  s.medium,
  s.classification,
  FLOOR(s.object_begin_date / 100) + 1 AS century,
  CAST(JSON_VALUE(p.parsed_json, '$.landscape.score') AS FLOAT64) AS landscape,
  CAST(JSON_VALUE(p.parsed_json, '$.plants.score') AS FLOAT64) AS plants,
  CAST(JSON_VALUE(p.parsed_json, '$.buildings.score') AS FLOAT64) AS buildings,
  CAST(JSON_VALUE(p.parsed_json, '$.food.score') AS FLOAT64) AS food,
  CAST(JSON_VALUE(p.parsed_json, '$.people.score') AS FLOAT64) AS people,
  CAST(JSON_VALUE(p.parsed_json, '$.animals.score') AS FLOAT64) AS animals,
  CAST(JSON_VALUE(p.parsed_json, '$.happiness.score') AS FLOAT64) AS happiness,
  CAST(JSON_VALUE(p.parsed_json, '$.love.score') AS FLOAT64) AS love,
  CAST(JSON_VALUE(p.parsed_json, '$.sadness.score') AS FLOAT64) AS sadness,
  CAST(JSON_VALUE(p.parsed_json, '$.fear.score') AS FLOAT64) AS fear,
  CAST(JSON_VALUE(p.parsed_json, '$.mystery.score') AS FLOAT64) AS mystery,
  CAST(JSON_VALUE(p.parsed_json, '$.confusion.score') AS FLOAT64) AS confusion,
  CAST(JSON_VALUE(p.parsed_json, '$.bright.score') AS FLOAT64) AS bright,
  CAST(JSON_VALUE(p.parsed_json, '$.dark.score') AS FLOAT64) AS dark
FROM
  (
    SELECT uri, result, SAFE.PARSE_JSON(REGEXP_EXTRACT(result, r'\{[\s\S]*\}')) AS parsed_json
    FROM `image_analysis.predicted_results`
  ) p
JOIN `image_analysis.sampled_images` s
  ON p.uri = s.uri
WHERE p.parsed_json IS NOT NULL