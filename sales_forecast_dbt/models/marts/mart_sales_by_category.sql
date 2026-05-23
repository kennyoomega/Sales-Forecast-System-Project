-- models/marts/mart_sales_by_category.sql
-- Purpose: Category + Sub-Category performance
-- Replaces: eda_v1.0 plot_category() and plot_subcategory_topn() logic

SELECT
    category,
    sub_category,
    ROUND(SUM(sales), 2)                                    AS total_sales,
    ROUND(SUM(profit), 2)                                   AS total_profit,
    SUM(quantity)                                           AS total_quantity,
    COUNT(DISTINCT order_id)                                AS order_count,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2)    AS profit_margin_pct,
    ROUND(SUM(sales) / NULLIF(SUM(quantity), 0), 2)         AS avg_unit_price,
    ROUND(AVG(discount), 4)                                 AS avg_discount
FROM {{ ref('stg_superstore_orders') }}
GROUP BY category, sub_category
ORDER BY total_sales DESC