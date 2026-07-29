WITH ranked_history AS (
    SELECT
        month,
        total_sales,
        ROW_NUMBER() OVER (
            ORDER BY month DESC
        ) AS recency_rank
    FROM {{ ref('int_monthly_sales') }}
),

latest_six AS (
    SELECT
        month,
        total_sales,
        recency_rank
    FROM ranked_history
    WHERE recency_rank <= 6
),

expected AS (
    SELECT
        DATE_ADD(
            MAX(month),
            INTERVAL 1 MONTH
        ) AS expected_target_month,

        MAX(
            IF(recency_rank = 1, total_sales, NULL)
        ) AS expected_lag_1,

        MAX(
            IF(recency_rank = 2, total_sales, NULL)
        ) AS expected_lag_2,

        MAX(
            IF(recency_rank = 3, total_sales, NULL)
        ) AS expected_lag_3,

        EXTRACT(
            MONTH FROM DATE_ADD(
                MAX(month),
                INTERVAL 1 MONTH
            )
        ) AS expected_month_of_year,

        AVG(
            IF(recency_rank <= 3, total_sales, NULL)
        ) AS expected_rolling_mean_3,

        AVG(total_sales) AS expected_rolling_mean_6,

        COUNT(*) AS expected_history_count,
        DATE_DIFF(
            MAX(month),
            MIN(month),
            MONTH
        ) AS expected_month_span

    FROM latest_six
),

actual AS (
    SELECT *
    FROM {{ ref('mart_next_month_features') }}
)

SELECT
    actual.*
FROM actual
CROSS JOIN expected
WHERE
    expected.expected_history_count != 6
    OR expected.expected_month_span != 5

    OR actual.target_month
        != expected.expected_target_month

    OR actual.month_of_year
        != expected.expected_month_of_year

    OR ABS(
        CAST(actual.lag_1 AS FLOAT64)
        - CAST(expected.expected_lag_1 AS FLOAT64)
    ) > 0.000001

    OR ABS(
        CAST(actual.lag_2 AS FLOAT64)
        - CAST(expected.expected_lag_2 AS FLOAT64)
    ) > 0.000001

    OR ABS(
        CAST(actual.lag_3 AS FLOAT64)
        - CAST(expected.expected_lag_3 AS FLOAT64)
    ) > 0.000001

    OR ABS(
        CAST(actual.rolling_mean_3 AS FLOAT64)
        - CAST(expected.expected_rolling_mean_3 AS FLOAT64)
    ) > 0.000001

    OR ABS(
        CAST(actual.rolling_mean_6 AS FLOAT64)
        - CAST(expected.expected_rolling_mean_6 AS FLOAT64)
    ) > 0.000001
