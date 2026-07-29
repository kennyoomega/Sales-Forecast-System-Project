{{ config(materialized='view') }}

-- One row per calendar month.
-- Shared monthly source for analytics marts and forecasting feature models.

SELECT
    DATE_TRUNC(order_date, MONTH) AS month,
    SUM(sales) AS total_sales,
    SUM(profit) AS total_profit,
    COUNT(DISTINCT order_id) AS order_count,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM {{ ref('stg_superstore_orders') }}
GROUP BY month
