{{ config(materialized='table') }}

-- Historical training dataset for monthly sales forecasting.
-- One row per target month, using only the six completed months
-- before that target month.

WITH feature_windows AS (
    SELECT
        month AS target_month,
        total_sales AS target_sales,

        LAG(total_sales, 1) OVER (
            ORDER BY month
        ) AS lag_1,

        LAG(total_sales, 2) OVER (
            ORDER BY month
        ) AS lag_2,

        LAG(total_sales, 3) OVER (
            ORDER BY month
        ) AS lag_3,

        EXTRACT(MONTH FROM month) AS month_of_year,

        AVG(total_sales) OVER (
            ORDER BY month
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS rolling_mean_3,

        AVG(total_sales) OVER (
            ORDER BY month
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
        ) AS rolling_mean_6,

        COUNT(total_sales) OVER (
            ORDER BY month
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
        ) AS history_month_count,

        LAG(month, 6) OVER (
            ORDER BY month
        ) AS history_start_month

    FROM {{ ref('int_monthly_sales') }}
),

complete_history AS (
    SELECT
        target_month,
        target_sales,
        lag_1,
        lag_2,
        lag_3,
        month_of_year,
        rolling_mean_3,
        rolling_mean_6
    FROM feature_windows
    WHERE
        history_month_count = 6
        AND DATE_DIFF(
            target_month,
            history_start_month,
            MONTH
        ) = 6
)

SELECT *
FROM complete_history
