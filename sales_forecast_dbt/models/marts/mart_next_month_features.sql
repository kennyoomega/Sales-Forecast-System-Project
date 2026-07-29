{{ config(materialized='table') }}

-- Feature row for forecasting the month immediately after
-- the latest completed month in int_monthly_sales.
-- Returns exactly one row when six consecutive months are available.

WITH ranked_history AS (
    SELECT
        month,
        total_sales,
        ROW_NUMBER() OVER (
            ORDER BY month DESC
        ) AS recency_rank
    FROM {{ ref('int_monthly_sales') }}
),

latest_six_months AS (
    SELECT
        month,
        total_sales,
        recency_rank
    FROM ranked_history
    WHERE recency_rank <= 6
),

feature_values AS (
    SELECT
        COUNT(*) AS history_month_count,
        MIN(month) AS history_start_month,
        MAX(month) AS history_end_month,

        MAX(
            IF(recency_rank = 1, total_sales, NULL)
        ) AS lag_1,

        MAX(
            IF(recency_rank = 2, total_sales, NULL)
        ) AS lag_2,

        MAX(
            IF(recency_rank = 3, total_sales, NULL)
        ) AS lag_3,

        AVG(
            IF(recency_rank <= 3, total_sales, NULL)
        ) AS rolling_mean_3,

        AVG(total_sales) AS rolling_mean_6

    FROM latest_six_months
)

SELECT
    DATE_ADD(
        history_end_month,
        INTERVAL 1 MONTH
    ) AS target_month,

    lag_1,
    lag_2,
    lag_3,

    EXTRACT(
        MONTH FROM DATE_ADD(
            history_end_month,
            INTERVAL 1 MONTH
        )
    ) AS month_of_year,

    rolling_mean_3,
    rolling_mean_6

FROM feature_values
WHERE
    history_month_count = 6
    AND DATE_DIFF(
        history_end_month,
        history_start_month,
        MONTH
    ) = 5
