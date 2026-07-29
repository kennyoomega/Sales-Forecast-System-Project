"""Train monthly sales forecasting models from dbt feature marts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.bq_client import load_forecast_training, load_monthly_sales
from src.feature_contract import (
    FEATURE_COLUMNS,
    validate_model_feature_names,
    validate_training_frame,
)

try:
    from xgboost import XGBRegressor

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


@dataclass(frozen=True)
class SplitData:
    """Chronological train and hold-out datasets."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    """Mean absolute percentage error in percent."""

    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    nonzero = actual != 0

    if not nonzero.any():
        return float("nan")

    return float(
        np.mean(
            np.abs(
                (actual[nonzero] - predicted[nonzero])
                / actual[nonzero]
            )
        )
        * 100
    )


def smape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    """Symmetric mean absolute percentage error in percent."""

    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    denominator = np.abs(actual) + np.abs(predicted)
    denominator = np.where(denominator == 0, 1e-8, denominator)

    return float(
        np.mean(
            2 * np.abs(predicted - actual) / denominator
        )
        * 100
    )


def rmse(y_true: pd.Series, y_pred: np.ndarray) -> float:
    """Root mean squared error."""

    return float(
        np.sqrt(
            mean_squared_error(y_true, y_pred)
        )
    )


def split_train_test(
    training_frame: pd.DataFrame,
    horizon: int,
) -> SplitData:
    """Use the latest horizon months as a chronological hold-out."""

    if horizon < 1:
        raise ValueError("horizon must be at least 1.")

    if len(training_frame) <= horizon:
        raise ValueError(
            "Training feature mart does not contain enough rows "
            f"for horizon={horizon}."
        )

    X = (
        training_frame
        .loc[:, FEATURE_COLUMNS]
        .astype(float)
    )
    y = training_frame["target_sales"].astype(float)

    return SplitData(
        X_train=X.iloc[:-horizon],
        X_test=X.iloc[-horizon:],
        y_train=y.iloc[:-horizon],
        y_test=y.iloc[-horizon:],
    )


def create_model(model_name: str):
    """Create a fresh forecasting estimator."""

    if model_name == "rf":
        return RandomForestRegressor(
            n_estimators=600,
            max_depth=12,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

    if model_name == "xgb":
        if not HAS_XGBOOST:
            raise RuntimeError(
                "XGBoost is not installed."
            )

        return XGBRegressor(
            n_estimators=600,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=42,
            tree_method="hist",
        )

    raise ValueError(
        f"Unsupported model: {model_name}"
    )


def load_monthly_series() -> pd.Series:
    """Load and validate the complete monthly sales history."""

    frame = load_monthly_sales().copy()

    required_columns = {"month", "total_sales"}
    missing_columns = required_columns.difference(frame.columns)

    if missing_columns:
        raise ValueError(
            "Monthly sales query is missing columns: "
            + ", ".join(sorted(missing_columns))
        )

    frame["month"] = pd.to_datetime(
        frame["month"],
        errors="coerce",
    )
    frame["total_sales"] = pd.to_numeric(
        frame["total_sales"],
        errors="coerce",
    )

    if frame[["month", "total_sales"]].isna().any().any():
        raise ValueError(
            "Monthly sales contains invalid dates or sales values."
        )

    if frame["month"].duplicated().any():
        raise ValueError(
            "Monthly sales contains duplicate months."
        )

    series = (
        frame
        .sort_values("month")
        .set_index("month")["total_sales"]
        .astype(float)
    )
    series.name = "Sales"

    expected_months = pd.date_range(
        start=series.index.min(),
        end=series.index.max(),
        freq="MS",
    )

    if not series.index.equals(expected_months):
        raise ValueError(
            "Monthly sales history contains missing months."
        )

    return series


def build_seasonal_naive_baseline(
    monthly_sales: pd.Series,
    target_index: pd.DatetimeIndex,
) -> pd.Series:
    """Use the same month last year, falling back to the prior month."""

    last_year = monthly_sales.shift(12).reindex(target_index)
    previous_month = monthly_sales.shift(1).reindex(target_index)
    baseline = last_year.fillna(previous_month)

    if baseline.isna().any():
        raise ValueError(
            "Could not construct a baseline for every hold-out month."
        )

    baseline.name = "Baseline"
    return baseline


def calculate_metrics(
    actual: pd.Series,
    predicted: pd.Series,
) -> dict[str, float]:
    """Calculate the common regression metrics."""

    return {
        "MAPE": mape(actual, predicted.to_numpy()),
        "sMAPE": smape(actual, predicted.to_numpy()),
        "MAE": float(
            mean_absolute_error(actual, predicted)
        ),
        "RMSE": rmse(actual, predicted.to_numpy()),
    }


def save_evaluation_plot(
    monthly_sales: pd.Series,
    evaluation: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save actual, model, and baseline values for the hold-out."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cutoff = evaluation.index.min()

    plt.figure(figsize=(10, 5))
    plt.plot(
        monthly_sales[monthly_sales.index < cutoff],
        label="History",
        linewidth=2,
    )
    plt.plot(
        evaluation.index,
        evaluation["Actual"],
        label="Hold-out Actual",
        linestyle="--",
        linewidth=2,
    )
    plt.plot(
        evaluation.index,
        evaluation["Forecast"],
        label="Model Forecast",
        linewidth=2,
    )
    plt.plot(
        evaluation.index,
        evaluation["Baseline"],
        label="Seasonal-Naive Baseline",
        linewidth=2,
    )
    plt.title("Monthly Sales Forecast Evaluation")
    plt.xlabel("Month")
    plt.ylabel("Sales")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def json_safe(value: Any) -> Any:
    """Convert NumPy and timestamp values into JSON-compatible values."""

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        return float(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Train a monthly sales forecasting model "
            "from dbt-generated BigQuery features."
        )
    )
    parser.add_argument(
        "--model",
        choices=("rf", "xgb"),
        default="rf",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=3,
        help="Number of latest months used for hold-out evaluation.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("reports"),
    )
    args = parser.parse_args()

    print(
        "[SOURCE] Loading BigQuery mart_forecast_training..."
    )
    training_frame = validate_training_frame(
        load_forecast_training()
    )
    monthly_sales = load_monthly_series()

    split = split_train_test(
        training_frame,
        horizon=args.horizon,
    )

    print(
        f"[DATA] training_rows={len(split.X_train)}, "
        f"holdout_rows={len(split.X_test)}"
    )
    print(
        f"[DATA] train_range="
        f"{split.X_train.index.min().date()} to "
        f"{split.X_train.index.max().date()}"
    )
    print(
        f"[DATA] holdout_range="
        f"{split.X_test.index.min().date()} to "
        f"{split.X_test.index.max().date()}"
    )

    # Evaluation fit: train only on data before the hold-out.
    evaluation_model = create_model(args.model)
    evaluation_model.fit(
        split.X_train,
        split.y_train,
    )
    validate_model_feature_names(
        getattr(
            evaluation_model,
            "feature_names_in_",
            None,
        )
    )

    forecast = pd.Series(
        evaluation_model.predict(split.X_test),
        index=split.y_test.index,
        name="Forecast",
    )
    baseline = build_seasonal_naive_baseline(
        monthly_sales,
        split.y_test.index,
    )

    evaluation = pd.DataFrame(
        {
            "Actual": split.y_test,
            "Forecast": forecast,
            "Baseline": baseline,
        }
    )

    metrics = {
        "Baseline": calculate_metrics(
            evaluation["Actual"],
            evaluation["Baseline"],
        ),
        "Model": calculate_metrics(
            evaluation["Actual"],
            evaluation["Forecast"],
        ),
    }

    print("[METRICS] Baseline:", metrics["Baseline"])
    print("[METRICS] Model   :", metrics["Model"])

    # Final fit: retrain on every validated row before saving for serving.
    full_X = (
        training_frame
        .loc[:, FEATURE_COLUMNS]
        .astype(float)
    )
    full_y = training_frame["target_sales"].astype(float)

    final_model = create_model(args.model)
    final_model.fit(full_X, full_y)
    validate_model_feature_names(
        getattr(
            final_model,
            "feature_names_in_",
            None,
        )
    )

    models_dir = args.outdir / "models"
    figures_dir = args.outdir / "figures"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = (
        models_dir
        / f"sales_forecast_{args.model}.pkl"
    )
    evaluation_path = (
        args.outdir
        / f"forecast_evaluation_{args.model}.csv"
    )
    metrics_path = (
        args.outdir
        / f"training_metrics_{args.model}.json"
    )
    figure_path = (
        figures_dir
        / f"forecast_vs_actual_{args.model}.png"
    )

    joblib.dump(final_model, model_path)
    evaluation.to_csv(
        evaluation_path,
        index_label="target_month",
    )
    save_evaluation_plot(
        monthly_sales,
        evaluation,
        figure_path,
    )

    report = {
        "trained_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "model": args.model,
        "source": "mart_forecast_training",
        "feature_columns": list(FEATURE_COLUMNS),
        "training_rows_total": len(training_frame),
        "evaluation_training_rows": len(split.X_train),
        "holdout_rows": len(split.X_test),
        "horizon": args.horizon,
        "training_start": training_frame.index.min(),
        "training_end": training_frame.index.max(),
        "holdout_start": split.X_test.index.min(),
        "holdout_end": split.X_test.index.max(),
        "metrics": metrics,
    }

    metrics_path.write_text(
        json.dumps(
            report,
            indent=2,
            default=json_safe,
        ),
        encoding="utf-8",
    )

    print(f"[OK] Final model: {model_path}")
    print(f"[OK] Metrics:     {metrics_path}")
    print(f"[OK] Evaluation:  {evaluation_path}")
    print(f"[OK] Figure:      {figure_path}")


if __name__ == "__main__":
    main()
