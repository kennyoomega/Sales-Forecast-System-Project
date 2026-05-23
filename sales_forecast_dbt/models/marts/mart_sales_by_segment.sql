-- models/marts/mart_sales_by_segment.sql
-- Purpose: Monthly sales by customer segment

SELECT
    DATE_TRUNC(order_date, MONTH)                           AS month,
    segment,
    ROUND(SUM(sales), 2)                                    AS total_sales,
    ROUND(SUM(profit), 2)                                   AS total_profit,
    COUNT(DISTINCT order_id)                                AS order_count,
    COUNT(DISTINCT customer_id)                             AS unique_customers,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2)    AS profit_margin_pct
FROM {{ ref('stg_superstore_orders') }}
GROUP BY 1, 2
ORDER BY 1, total_sales DESC