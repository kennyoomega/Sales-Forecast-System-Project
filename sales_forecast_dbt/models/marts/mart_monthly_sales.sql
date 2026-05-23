-- models/marts/mart_monthly_sales.sql
-- Purpose: Monthly total sales with pre-computed lag features
-- Replaces: eda_v1.2.py load_and_monthly_aggregate() + lag feature logic

WITH monthly AS (
    SELECT
        DATE_TRUNC(order_date, MONTH)                           AS month,
        ROUND(SUM(sales), 2)                                    AS total_sales,
        COUNT(DISTINCT order_id)                                AS order_count,
        COUNT(DISTINCT customer_id)                             AS unique_customers,
        ROUND(SUM(profit), 2)                                   AS total_profit,
        ROUND(SUM(profit) / NULLIF(SUM(sales), 0), 4)          AS profit_margin
    FROM {{ ref('stg_superstore_orders') }}
    GROUP BY 1
    ORDER BY 1
)

SELECT
    month,
    total_sales,
    order_count,
    unique_customers,
    total_profit,
    profit_margin,
    LAG(total_sales, 1) OVER (ORDER BY month)                                    AS lag_1,
    LAG(total_sales, 2) OVER (ORDER BY month)                                    AS lag_2,
    LAG(total_sales, 3) OVER (ORDER BY month)                                    AS lag_3,
    ROUND(AVG(total_sales) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_mean_3,
    ROUND(AVG(total_sales) OVER (ORDER BY month ROWS BETWEEN 5 PRECEDING AND CURRENT ROW), 2) AS rolling_mean_6,
    EXTRACT(MONTH FROM month)                                                     AS month_of_year
FROM monthly