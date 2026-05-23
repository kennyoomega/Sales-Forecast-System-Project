-- models/marts/mart_sales_by_region.sql
-- Purpose: Geographic breakdown
-- Replaces: eda_v1.0 plot_geo_topn() logic

SELECT
    region,
    state,
    ROUND(SUM(sales), 2)                                    AS total_sales,
    ROUND(SUM(profit), 2)                                   AS total_profit,
    COUNT(DISTINCT order_id)                                AS order_count,
    COUNT(DISTINCT customer_id)                             AS unique_customers,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2)    AS profit_margin_pct,
    ROUND(SUM(sales) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_order_value
FROM {{ ref('stg_superstore_orders') }}
GROUP BY region, state
ORDER BY total_sales DESC