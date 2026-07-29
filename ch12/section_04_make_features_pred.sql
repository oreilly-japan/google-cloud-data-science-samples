/*
  Step 1: データの前処理 (欠損値除去、キャンセルデータの除外、購入金額の計算)
*/
WITH clean_data AS (
  SELECT
    customer_id,
    invoice,
    stock_code,
    description,
    quantity,
    price,
    country,
    invoice_date AS timestamp,
    DATE(invoice_date) AS date,
    quantity * price AS purchase_amount
  FROM
    uci_data.online_retail_ii
  WHERE
    customer_id IS NOT NULL
    AND invoice not LIKE "%C%"
    AND quantity * price > 0
),

/*
  Step 2: aggregate_2nd_level関数の処理の準備 (Invoice単位、Date単位での合計金額を計算しておく)
*/
invoice_summary AS (
  SELECT
    customer_id,
    invoice,
    MIN(date) as date,
    SUM(purchase_amount) AS invoice_amount
  FROM clean_data
  GROUP BY 1, 2
),

date_summary AS (
  SELECT
    customer_id,
    date,
    SUM(purchase_amount) AS date_amount
  FROM clean_data
  GROUP BY 1, 2
),

/*
  Step 3: 予測日の生成 (本番: CURRENT_DATE(), テスト: "2011-12-01")
*/
prediction_dates AS (
  --SELECT CURRENT_DATE() AS date  -- 本番用
  SELECT DATE("2011-12-01") AS date  -- テスト用
),

anchors AS (
  -- 顧客 × 予測日 の組み合わせを作成（その日以前に購入履歴がある顧客のみ）
  SELECT DISTINCT t.customer_id, p.date AS prediction_date
  FROM clean_data t
  CROSS JOIN prediction_dates p
  WHERE t.date < p.date
),

/*
  Step 4: 特徴量の作成 (create_features関数)
*/
base AS (
  SELECT
    a.customer_id,
    a.prediction_date,
    APPROX_TOP_COUNT(c.country, 1)[OFFSET(0)].value AS country_mode,
    COUNT(DISTINCT c.country) AS country_nunique,
    DATE_DIFF(a.prediction_date, MIN(c.date), DAY) AS elapsed_days_from_first,
    DATE_DIFF(a.prediction_date, MAX(c.date), DAY) AS elapsed_days_from_last
  FROM anchors a
  LEFT JOIN clean_data c
    ON a.customer_id = c.customer_id AND c.date < a.prediction_date
  WHERE c.date >= DATE_SUB(a.prediction_date, INTERVAL 90 DAY)
  GROUP BY 1, 2
),

agg AS (
  SELECT
    a.customer_id,
    a.prediction_date,
    COUNT(c.invoice) AS record_cnt,
    COUNT(DISTINCT c.invoice) AS invoice_nunique,
    COUNT(DISTINCT c.stock_code) AS stock_nunique,
    COUNT(DISTINCT c.timestamp) AS timestamp_nunique,
    COUNT(DISTINCT c.date) AS date_nunique,
    SUM(c.purchase_amount) AS purchase_amount_sum
  FROM anchors a
  LEFT JOIN clean_data c
    ON a.customer_id = c.customer_id AND c.date < a.prediction_date
  WHERE c.date >= DATE_SUB(a.prediction_date, INTERVAL 90 DAY)
  GROUP BY 1, 2
),

invoice_agg AS (
  SELECT
    a.customer_id,
    a.prediction_date,
    MIN(i.invoice_amount) AS purchase_amount_by_invoice_min,
    MAX(i.invoice_amount) AS purchase_amount_by_invoice_max,
    AVG(i.invoice_amount) AS purchase_amount_by_invoice_mean,
    AVG(i.invoice_amount) AS purchase_amount_by_invoice_mean
  FROM anchors a
  LEFT JOIN invoice_summary i
    ON a.customer_id = i.customer_id AND i.date < a.prediction_date
  WHERE i.date >= DATE_SUB(a.prediction_date, INTERVAL 90 DAY)
  GROUP BY 1, 2
),

date_agg AS (
  SELECT
    a.customer_id,
    a.prediction_date,
    MIN(d.date_amount) AS purchase_amount_by_date_min,
    MAX(d.date_amount) AS purchase_amount_by_date_max,
    AVG(d.date_amount) AS purchase_amount_by_date_mean
  FROM anchors a
  LEFT JOIN date_summary d
    ON a.customer_id = d.customer_id AND d.date < a.prediction_date
  WHERE d.date >= DATE_SUB(a.prediction_date, INTERVAL 90 DAY)
  GROUP BY 1, 2
),

features AS (
  SELECT
    b.*,
    a.* EXCEPT (customer_id, prediction_date),
    i.* EXCEPT (customer_id, prediction_date),
    d.* EXCEPT (customer_id, prediction_date),
  FROM base b
  LEFT JOIN agg a
    ON b.customer_id = a.customer_id AND b.prediction_date = a.prediction_date
  LEFT JOIN invoice_agg i
    ON b.customer_id = i.customer_id AND b.prediction_date = i.prediction_date
  LEFT JOIN date_agg d
    ON b.customer_id = d.customer_id AND b.prediction_date = d.prediction_date
)

/*
  目的変数とデータ分割ラベルは不要なためそのまま出力
*/
SELECT *
FROM features