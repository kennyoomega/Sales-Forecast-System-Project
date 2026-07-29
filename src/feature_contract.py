"""Shared schema contract for dbt-generated forecasting features.

dbt owns feature calculation. Python only validates and consumes the
resulting training and prediction feature tables.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


FEATURE_COLUMNS: tuple[str, ...] = (
    "lag_1",
    "lag_2",
    "lag_3",
    "month_of_year",
    "rolling_mean_3",
    "rolling_mean_6",
)

TRAINING_COLUMNS: tuple[str, ...] = (
    "target_month",
    "target_sales",
    *FEATURE_COLUMNS,
)

PREDICTION_COLUMNS: tuple[str, ...] = (
    "target_month",
    *FEATURE_COLUMNS,
)


class FeatureContractError(ValueError):
    """Raised when warehouse features do not match the expected contract."""


def _require_columns(
    frame: pd.DataFrame,
    required_columns: Sequence[str],
) -> None:
    missing_columns = [
        column
        for column in required_columns
        if column not in frame.columns
    ]

    if missing_columns:
        raise FeatureContractError(
            "Missing required feature columns: "
            + ", ".join(missing_columns)
        )


def _validate_feature_values(frame: pd.DataFrame) -> None:
    feature_frame = frame.loc[:, FEATURE_COLUMNS]

    if feature_frame.isna().any().any():
        null_columns = feature_frame.columns[
            feature_frame.isna().any()
        ].tolist()

        raise FeatureContractError(
            "Forecast features contain null values in: "
            + ", ".join(null_columns)
        )

    numeric_features = feature_frame.apply(
        pd.to_numeric,
        errors="coerce",
    )

    if numeric_features.isna().any().any():
        invalid_columns = numeric_features.columns[
            numeric_features.isna().any()
        ].tolist()

        raise FeatureContractError(
            "Forecast features contain non-numeric values in: "
            + ", ".join(invalid_columns)
        )

    invalid_months = ~numeric_features["month_of_year"].between(1, 12)

    if invalid_months.any():
        raise FeatureContractError(
            "month_of_year must be between 1 and 12."
        )


def validate_training_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the dbt training feature mart."""

    if not isinstance(frame, pd.DataFrame):
        raise FeatureContractError(
            "Training features must be provided as a pandas DataFrame."
        )

    if frame.empty:
        raise FeatureContractError(
            "Training feature mart returned no rows."
        )

    _require_columns(frame, TRAINING_COLUMNS)

    validated = frame.loc[:, TRAINING_COLUMNS].copy()
    validated["target_month"] = pd.to_datetime(
        validated["target_month"],
        errors="coerce",
    )
    validated["target_sales"] = pd.to_numeric(
        validated["target_sales"],
        errors="coerce",
    )

    if validated["target_month"].isna().any():
        raise FeatureContractError(
            "target_month contains invalid dates."
        )

    if validated["target_month"].duplicated().any():
        raise FeatureContractError(
            "target_month must be unique."
        )

    if validated["target_sales"].isna().any():
        raise FeatureContractError(
            "target_sales contains null or non-numeric values."
        )

    _validate_feature_values(validated)

    validated = (
        validated
        .sort_values("target_month")
        .set_index("target_month")
    )

    return validated


def validate_prediction_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the single row generated for the next forecast month."""

    if not isinstance(frame, pd.DataFrame):
        raise FeatureContractError(
            "Prediction features must be provided as a pandas DataFrame."
        )

    if len(frame) != 1:
        raise FeatureContractError(
            "Prediction feature mart must return exactly one row; "
            f"received {len(frame)}."
        )

    _require_columns(frame, PREDICTION_COLUMNS)

    validated = frame.loc[:, PREDICTION_COLUMNS].copy()
    validated["target_month"] = pd.to_datetime(
        validated["target_month"],
        errors="coerce",
    )

    if validated["target_month"].isna().any():
        raise FeatureContractError(
            "target_month contains an invalid date."
        )

    _validate_feature_values(validated)

    return validated


def validate_model_feature_names(
    feature_names: Sequence[str] | None,
) -> None:
    """Ensure the trained model expects the exact dbt feature contract."""

    if feature_names is None:
        raise FeatureContractError(
            "The trained model does not expose feature names."
        )

    actual_columns = tuple(str(name) for name in feature_names)

    if actual_columns != FEATURE_COLUMNS:
        raise FeatureContractError(
            "Model feature contract mismatch. "
            f"Expected {list(FEATURE_COLUMNS)}, "
            f"received {list(actual_columns)}."
        )
