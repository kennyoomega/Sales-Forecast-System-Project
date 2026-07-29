WITH actual AS (
    SELECT *
    FROM {{ ref('mart_forecast_training') }}
),

expected AS (
    SELECT
        actual.target_month,

        target_month_sales.total_sales AS expected_target_sales,
        month_1.total_sales AS expected_lag_1,
        month_2.total_sales AS expected_lag_2,
        month_3.total_sales AS expected_lag_3,

        EXTRACT(
            MONTH FROM actual.target_month
        ) AS expected_month_of_year,

        (
            month_1.total_sales
            + month_2.total_sales
            + month_3.total_sales
        ) / 3 AS expected_rolling_mean_3,

        (
            month_1.total_sales
            + month_2.total_sales
            + month_3.total_sales
            + month_4.total_sales
            + month_5.total_sales
            + month_6.total_sales
        ) / 6 AS expected_rolling_mean_6,

        month_4.total_sales AS month_4_sales,
        month_5.total_sales AS month_5_sales,
        month_6.total_sales AS month_6_sales

    FROM actual

    LEFT JOIN {{ ref('int_monthly_sales') }} AS target_month_sales
        ON target_month_sales.month = actual.target_month

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_1
        ON month_1.month = DATE_SUB(
            actual.target_month,
            INTERVAL 1 MONTH
        )

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_2
        ON month_2.month = DATE_SUB(
            actual.target_month,
            INTERVAL 2 MONTH
        )

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_3
        ON month_3.month = DATE_SUB(
            actual.target_month,
            INTERVAL 3 MONTH
        )

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_4
        ON month_4.month = DATE_SUB(
            actual.target_month,
            INTERVAL 4 MONTH
        )

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_5
        ON month_5.month = DATE_SUB(
            actual.target_month,
            INTERVAL 5 MONTH
        )

    LEFT JOIN {{ ref('int_monthly_sales') }} AS month_6
        ON month_6.month = DATE_SUB(
            actual.target_month,
            INTERVAL 6 MONTH
        )
)

SELECT
    actual.*
FROM actual
INNER JOIN expected
    USING (target_month)
WHERE
    expected.expected_target_sales IS NULL
    OR expected.expected_lag_1 IS NULL
    OR expected.expected_lag_2 IS NULL
    OR expected.expected_lag_3 IS NULL
    OR expected.month_4_sales IS NULL
    OR expected.month_5_sales IS NULL
    OR expected.month_6_sales IS NULL

    OR ABS(
        CAST(actual.target_sales AS FLOAT64)
        - CAST(expected.expected_target_sales AS FLOAT64)
    ) > 0.000001

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

    OR actual.month_of_year
        != expected.expected_month_of_year

    OR ABS(
        CAST(actual.rolling_mean_3 AS FLOAT64)
        - CAST(expected.expected_rolling_mean_3 AS FLOAT64)
    ) > 0.000001

    OR ABS(
        CAST(actual.rolling_mean_6 AS FLOAT64)
        - CAST(expected.expected_rolling_mean_6 AS FLOAT64)
    ) > 0.000001
