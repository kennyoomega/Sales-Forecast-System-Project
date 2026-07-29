WITH row_count AS (
    SELECT COUNT(*) AS total_rows
    FROM {{ ref('mart_next_month_features') }}
)

SELECT *
FROM row_count
WHERE total_rows != 1
