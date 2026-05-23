-- models/staging/stg_superstore_orders.sql
-- Purpose: Clean and standardize raw Superstore data
-- ONE job: rename columns, cast types, nothing else

WITH source AS (
    SELECT * FROM {{ source('raw', 'superstore_orders') }}
),

renamed AS (
    SELECT
        -- Order identifiers
        `Row ID`          AS row_id,
        `Order ID`        AS order_id,
        `Order Date`      AS order_date,
        `Ship Date`       AS ship_date,
        `Ship Mode`       AS ship_mode,

        -- Customer dimensions
        `Customer ID`     AS customer_id,
        `Customer Name`   AS customer_name,
        `Segment`         AS segment,

        -- Geography
        `Country`         AS country,
        `City`            AS city,
        `State`           AS state,
        `Postal Code`     AS postal_code,
        `Region`          AS region,

        -- Product dimensions
        `Product ID`      AS product_id,
        `Category`        AS category,
        `Sub-Category`    AS sub_category,
        `Product Name`    AS product_name,

        -- Metrics
        CAST(`Sales`    AS FLOAT64) AS sales,
        CAST(`Quantity` AS INT64)   AS quantity,
        CAST(`Discount` AS FLOAT64) AS discount,
        CAST(`Profit`   AS FLOAT64) AS profit

    FROM source
    WHERE `Order Date` IS NOT NULL
      AND `Sales` IS NOT NULL
)

SELECT * FROM renamed