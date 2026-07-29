-- 1. プロンプトの定義
DECLARE analysis_prompt STRING;
SET analysis_prompt = """
与えられた画像を分析し、以下の各ラベルに対して 0.0 ~ 1.0 のスコアを割り当ててください。

- landscape
- people
- food
- plants
- buildings
- animals
- happiness
- love
- sadness
- fear
- mystery
- confusion
- bright
- dark

次のような出力形式で出力してください。"reason" にはスコアの理由を記述してください。
<出力形式>
{
  "landscape": {"score": [スコア], "reason": "[理由を記述]"},
  "people": {"score": [スコア], "reason": "[理由を記述]"},
  ...
}
</出力形式>
"""
;

-- 2. データセットの作成
CREATE SCHEMA IF NOT EXISTS `image_analysis`;

-- 3. Met の公開 GCS バケットを参照するオブジェクトテーブルの作成
CREATE OR REPLACE EXTERNAL TABLE `image_analysis.public_images`
WITH CONNECTION `us.gemini_conn`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://gcs-public-data--met/*.jpg'],
  max_staleness = INTERVAL 1 DAY, 
  metadata_cache_mode = 'AUTOMATIC'
);

-- 4. Gemini モデルの作成
CREATE OR REPLACE MODEL `image_analysis.gemini_25_flash_lite`
REMOTE WITH CONNECTION `us.gemini_conn`
OPTIONS (
  endpoint = 'gemini-2.5-flash-lite'
);

-- 5. 画像のフィルタリング
CREATE OR REPLACE TABLE `image_analysis.sampled_images` AS
SELECT p.*, i.* EXCEPT(title), o.* EXCEPT(object_id)
FROM `image_analysis.public_images` p
JOIN `bigquery-public-data.the_met.images` i
  ON p.uri = i.gcs_url
JOIN `bigquery-public-data.the_met.objects` o
  ON i.object_id = o.object_id
WHERE i.gcs_url IS NOT NULL
  AND o.object_begin_date IS NOT NULL
  AND o.culture IS NOT NULL
  AND o.classification IN ("Prints", "Drawings", "Paintings")
  AND ARRAY_REVERSE(SPLIT(i.gcs_url, '/'))[OFFSET(0)] = "0.jpg"
;

-- 6. 画像に対する推論の実行
CREATE OR REPLACE TABLE `image_analysis.predicted_results` AS
SELECT
  uri,
  result
FROM
  AI.GENERATE_TEXT(
    MODEL `image_analysis.gemini_25_flash_lite`,
    (SELECT uri, (analysis_prompt, ref) AS prompt FROM image_analysis.sampled_images),
    STRUCT(
      '{"generation_config":{"thinking_config": {"thinking_budget": 0}}}' AS model_params
    )
  );