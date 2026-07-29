CREATE OR REPLACE VIEW `image_analysis.century_culture_emotions` AS
SELECT
  century,
  culture,
  COUNT(*) AS image_count,
  COUNT(CASE WHEN happiness >= 0.6 THEN 1 ELSE NULL END) AS happiness,
  COUNT(CASE WHEN love >= 0.6 THEN 1 ELSE NULL END) AS love,
  COUNT(CASE WHEN sadness >= 0.6 THEN 1 ELSE NULL END) AS sadness,
  COUNT(CASE WHEN fear >= 0.6 THEN 1 ELSE NULL END) AS fear,
  COUNT(CASE WHEN mystery >= 0.6 THEN 1 ELSE NULL END) AS mystery,
  COUNT(CASE WHEN confusion >= 0.6 THEN 1 ELSE NULL END) AS confusion,
  COUNT(CASE WHEN bright >= 0.6 THEN 1 ELSE NULL END) AS bright,
  COUNT(CASE WHEN dark >= 0.6 THEN 1 ELSE NULL END) AS dark
FROM `image_analysis.enriched_results`
WHERE century IS NOT NULL
GROUP BY century, culture
HAVING COUNT(*) >= 10
ORDER BY culture;