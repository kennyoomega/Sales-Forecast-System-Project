-- models/marts/mart_product_performance.sql
-- Purpose: Product-level profitability with ranking
-- Window functions: RANK() + OVER PARTITION BY

WITH product_base AS (
    SELECT
        product_id,
        product_name,
        category,
        sub_category,
        ROUND(SUM(sales), 2)                                    AS total_sales,
        ROUND(SUM(profit), 2)                                   AS total_profit,
        SUM(quantity)                                           AS total_quantity,
        COUNT(DISTINCT order_id)                                AS order_count,
        ROUND(AVG(discount), 4)                                 AS avg_discount,
        ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2)    AS profit_margin_pct
    FROM {{ ref('stg_superstore_orders') }}
    GROUP BY product_id, product_name, category, sub_category
)

SELECT
    *,
    RANK() OVER (
        PARTITION BY sub_category
        ORDER BY total_sales DESC
    )                                                           AS rank_in_subcategory,
    ROUND(
        total_sales / NULLIF(SUM(total_sales) OVER (PARTITION BY category), 0) * 100,
        2
    )                                                           AS pct_of_category_sales
FROM product_base
ORDER BY total_sales DESC