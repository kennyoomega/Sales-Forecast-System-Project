"""BigQuery access layer for analytics and forecasting data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


PROJECT_ID: Final[str] = os.getenv(
    "BQ_PROJECT_ID",
    "peppy-ward-497115-k8",
)
DATASET: Final[str] = os.getenv(
    "BQ_DATASET",
    "analytics",
)
KEY_FILE: Final[str] = os.getenv(
    "BQ_KEY_FILE",
    "",
)

ANALYTICS_MARTS: Final[frozenset[str]] = frozenset(
    {
        "mart_monthly_sales",
        "mart_sales_by_category",
        "mart_sales_by_region",
        "mart_sales_by_segment",
        "mart_product_performance",
    }
)


def get_client() -> bigquery.Client:
    """Create a BigQuery client using a key file or ADC."""

    if KEY_FILE:
        key_path = Path(KEY_FILE)

        if not key_path.is_file():
            raise FileNotFoundError(
                f"BQ_KEY_FILE does not exist: {key_path}"
            )

        credentials = (
            service_account.Credentials
            .from_service_account_file(key_path)
        )

        return bigquery.Client(
            project=PROJECT_ID,
            credentials=credentials,
        )

    return bigquery.Client(project=PROJECT_ID)


def query_dataframe(query: str) -> pd.DataFrame:
    """Execute a BigQuery query and return a pandas DataFrame."""

    client = get_client()
    return client.query(query).to_dataframe()


def query_mart(
    model_name: str,
    limit: int = 1000,
) -> list[dict]:
    """Read an approved analytics mart for API endpoints."""

    if model_name not in ANALYTICS_MARTS:
        raise ValueError(
            f"Unsupported analytics mart: {model_name}"
        )

    if not isinstance(limit, int) or not 1 <= limit <= 10_000:
        raise ValueError(
            "limit must be an integer between 1 and 10000."
        )

    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET}.{model_name}`
        LIMIT {limit}
    """

    return [
        dict(row)
        for row in get_client().query(query).result()
    ]


def load_forecast_training() -> pd.DataFrame:
    """Load the tested dbt training feature mart."""

    query = f"""
        SELECT
            target_month,
            target_sales,
            lag_1,
            lag_2,
            lag_3,
            month_of_year,
            rolling_mean_3,
            rolling_mean_6
        FROM `{PROJECT_ID}.{DATASET}.mart_forecast_training`
        ORDER BY target_month
    """

    return query_dataframe(query)


def load_next_month_features() -> pd.DataFrame:
    """Load the single dbt feature row for online prediction."""

    query = f"""
        SELECT
            target_month,
            lag_1,
            lag_2,
            lag_3,
            month_of_year,
            rolling_mean_3,
            rolling_mean_6
        FROM `{PROJECT_ID}.{DATASET}.mart_next_month_features`
    """

    return query_dataframe(query)


def load_monthly_sales() -> pd.DataFrame:
    """Load the complete monthly series for reporting and baselines."""

    query = f"""
        SELECT
            month,
            total_sales
        FROM `{PROJECT_ID}.{DATASET}.int_monthly_sales`
        ORDER BY month
    """

    return query_dataframe(query)
