"""Compare five-feature and six-feature forecasting contracts.

The experiment uses expanding-window time-series validation:
- 5 validation folds
- 3 months per validation fold
- Random Forest and XGBoost
- identical training settings for both feature sets

This script does not overwrite production model files.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit


ROOT = Path(__file__).resolve().parents[1]
TRAINING_MODULE_PATH = ROOT / "src" / "eda_v1.2.py"
DATA_PATH = ROOT / "data" / "Superstore.csv"
REPORTS_DIR = ROOT / "reports"


FIVE_FEATURES = [
    "lag_1",
    "lag_2",
    "lag_3",
    "month",
    "roll_mean_3",
]

SIX_FEATURES = [
    *FIVE_FEATURES,
    "roll_mean_6",
]

FEATURE_SETS = {
    "five_features": FIVE_FEATURES,
    "six_features": SIX_FEATURES,
}


def load_training_module():
    """Load eda_v1.2.py despite the dot in its filename."""
    spec = importlib.util.spec_from_file_location(
        "forecast_training",
        TRAINING_MODULE_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load training module: {TRAINING_MODULE_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_configuration(
    *,
    df_features: pd.DataFrame,
    feature_set_name: str,
    feature_columns: list[str],
    model_name: str,
    trainer: Callable,
    training_module,
) -> list[dict]:
    """Evaluate one model and feature set across time-series folds."""
    X = df_features[feature_columns].astype(float)
    y = df_features["Sales"].astype(float)

    splitter = TimeSeriesSplit(
        n_splits=5,
        test_size=3,
    )

    fold_results: list[dict] = []

    for fold_number, (train_indices, test_indices) in enumerate(
        splitter.split(X),
        start=1,
    ):
        X_train = X.iloc[train_indices]
        X_test = X.iloc[test_indices]
        y_train = y.iloc[train_indices]
        y_test = y.iloc[test_indices]

        model = trainer(X_train, y_train)
        predictions = model.predict(X_test)

        fold_results.append(
            {
                "feature_set": feature_set_name,
                "feature_count": len(feature_columns),
                "model": model_name,
                "fold": fold_number,
                "train_start": X_train.index.min().date().isoformat(),
                "train_end": X_train.index.max().date().isoformat(),
                "test_start": X_test.index.min().date().isoformat(),
                "test_end": X_test.index.max().date().isoformat(),
                "rmse": training_module.rmse(y_test, predictions),
                "mae": float(mean_absolute_error(y_test, predictions)),
                "mape": training_module.mape(y_test, predictions),
                "smape": training_module.smape(y_test, predictions),
            }
        )

    return fold_results


def main() -> None:
    training = load_training_module()

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    print("[DATA] Loading Superstore CSV...")

    sales_series = training.load_and_monthly_aggregate(
        csv_path=DATA_PATH,
        date_col="Order Date",
        target_col="Sales",
        freq="MS",
        encoding="utf-8",
        sep=",",
    )

    df_features = training.add_lag_features(
        sales_series,
        n_lags=3,
    )

    print(
        "[DATA]",
        f"rows={len(df_features)},",
        f"start={df_features.index.min().date()},",
        f"end={df_features.index.max().date()}",
    )

    model_trainers = {
        "random_forest": training.train_rf,
    }

    if training._HAS_XGB:
        model_trainers["xgboost"] = training.train_xgb
    else:
        print("[WARN] XGBoost unavailable; only Random Forest will run.")

    all_results: list[dict] = []

    for feature_set_name, feature_columns in FEATURE_SETS.items():
        for model_name, trainer in model_trainers.items():
            print(
                f"[RUN] model={model_name}, "
                f"feature_set={feature_set_name}"
            )

            all_results.extend(
                evaluate_configuration(
                    df_features=df_features,
                    feature_set_name=feature_set_name,
                    feature_columns=feature_columns,
                    model_name=model_name,
                    trainer=trainer,
                    training_module=training,
                )
            )

    fold_results = pd.DataFrame(all_results)

    summary = (
        fold_results
        .groupby(
            ["model", "feature_set", "feature_count"],
            as_index=False,
        )
        .agg(
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            mae_mean=("mae", "mean"),
            mape_mean=("mape", "mean"),
            smape_mean=("smape", "mean"),
            smape_std=("smape", "std"),
        )
        .sort_values(
            ["model", "smape_mean"],
            ascending=[True, True],
        )
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    folds_path = REPORTS_DIR / "feature_set_comparison_folds.csv"
    summary_path = REPORTS_DIR / "feature_set_comparison_summary.csv"

    fold_results.to_csv(folds_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\n=== FEATURE SET COMPARISON ===")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print(f"\n[OK] Fold results: {folds_path}")
    print(f"[OK] Summary:      {summary_path}")


if __name__ == "__main__":
    main()