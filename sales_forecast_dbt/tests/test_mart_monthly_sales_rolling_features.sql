WITH expected_features AS (
    SELECT
        month,
        rolling_mean_3,
        rolling_mean_6,

        ROUND(
            AVG(total_sales) OVER (
                ORDER BY month
                ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
            ),
            2
        ) AS expected_rolling_mean_3,

        ROUND(
            AVG(total_sales) OVER (
                ORDER BY month
                ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
            ),
            2
        ) AS expected_rolling_mean_6

    FROM {{ ref('mart_monthly_sales') }}
)

SELECT *
FROM expected_features
WHERE
    COALESCE(rolling_mean_3, -1) != COALESCE(expected_rolling_mean_3, -1)
    OR
    COALESCE(rolling_mean_6, -1) != COALESCE(expected_rolling_mean_6, -1)