CREATE OR REPLACE VIEW `image_analysis.culture_subjects` AS
SELECT
  culture,
  COUNT(*) AS image_count,
  COUNT(CASE WHEN landscape >= 0.8 THEN 1 ELSE NULL END) AS landscape,
  COUNT(CASE WHEN people >= 0.8 THEN 1 ELSE NULL END) AS people,
  COUNT(CASE WHEN food >= 0.8 THEN 1 ELSE NULL END) AS food,
  COUNT(CASE WHEN plants >= 0.8 THEN 1 ELSE NULL END) AS plants,
  COUNT(CASE WHEN buildings >= 0.8 THEN 1 ELSE NULL END) AS buildings,
  COUNT(CASE WHEN animals >= 0.8 THEN 1 ELSE NULL END) AS animals
FROM `image_analysis.enriched_results`
WHERE culture IS NOT NULL
GROUP BY culture
HAVING COUNT(*) >= 10
ORDER BY image_count DESC;