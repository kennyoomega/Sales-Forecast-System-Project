-- Monthly sales KPIs for analytics dashboards and API consumers.
-- Grain: one row per calendar month.

SELECT
    month,
    ROUND(total_sales, 2) AS total_sales,
    order_count,
    unique_customers,
    ROUND(total_profit, 2) AS total_profit,
    ROUND(
        total_profit / NULLIF(total_sales, 0),
        4
    ) AS profit_margin
FROM {{ ref('int_monthly_sales') }}
ORDER BY month