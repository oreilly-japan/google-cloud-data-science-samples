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
  Step 3: 予測日の生成 ("2011-03-01" ~ "2011-11-01" を生成)
*/
prediction_dates AS (
  SELECT date 
  FROM UNNEST(GENERATE_DATE_ARRAY('2011-03-01', '2011-11-01', INTERVAL 1 MONTH)) AS date
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
),

/*
  Step 5: 目的変数の作成 (create_target関数)
*/
targets AS (
  SELECT
    a.customer_id,
    a.prediction_date,
    SUM(c.purchase_amount) AS target
  FROM anchors a
  LEFT JOIN clean_data c
    ON a.customer_id = c.customer_id
    AND c.date >= a.prediction_date
    AND c.date < DATE_ADD(a.prediction_date, INTERVAL 30 DAY)
  GROUP BY 1, 2
),

/*
  Step 6: 特徴量、目的変数の結合 (AutoMLでのデータ分割のためにsplit_labelを用意)
*/
summary AS (
  SELECT
    f.*,
    CASE
      WHEN f.prediction_date IN ("2011-03-01", "2011-04-01", "2011-05-01", "2011-06-01", "2011-07-01", "2011-08-01") THEN "TRAIN"
      WHEN f.prediction_date IN ("2011-09-01", "2011-10-01") THEN "VALIDATE"
      WHEN f.prediction_date IN ("2011-11-01") THEN "TEST"
      ELSE NULL
    END AS split_label,
    COALESCE(t.target, 0) AS target
  FROM features f
  LEFT JOIN targets t
    ON f.customer_id = t.customer_id AND f.prediction_date = t.prediction_date
  WHERE
    f.prediction_date <= DATE('2011-11-01')
)

SELECT *
FROM summary