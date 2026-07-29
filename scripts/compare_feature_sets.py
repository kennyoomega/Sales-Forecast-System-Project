"""Compare five- and six-feature forecasting contracts.

The experiment consumes the validated dbt training mart and uses the
same model configurations as the production training pipeline.

It does not overwrite production model artifacts.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.bq_client import load_forecast_training
from src.feature_contract import (
    FEATURE_COLUMNS,
    validate_training_frame,
)
from src.train_forecast import (
    HAS_XGBOOST,
    calculate_metrics,
    create_model,
)


REPORTS_DIR = Path("reports")

N_SPLITS = 5
TEST_SIZE = 3

FIVE_FEATURES = tuple(
    feature
    for feature in FEATURE_COLUMNS
    if feature != "rolling_mean_6"
)

SIX_FEATURES = tuple(FEATURE_COLUMNS)

FEATURE_SETS = {
    "five_features": FIVE_FEATURES,
    "six_features": SIX_FEATURES,
}


def validate_experiment_feature_names(
    model,
    expected_columns: tuple[str, ...],
) -> None:
    """Confirm that a fitted estimator retained the requested column order."""

    actual_columns = getattr(
        model,
        "feature_names_in_",
        None,
    )

    if actual_columns is None:
        raise ValueError(
            "Fitted model does not expose feature_names_in_."
        )

    actual_columns = tuple(actual_columns)

    if actual_columns != expected_columns:
        raise ValueError(
            "Experiment model feature mismatch. "
            f"Expected {expected_columns}, "
            f"received {actual_columns}."
        )


def evaluate_configuration(
    *,
    training_frame: pd.DataFrame,
    feature_set_name: str,
    feature_columns: tuple[str, ...],
    model_name: str,
) -> list[dict]:
    """Evaluate one model and feature set across chronological folds."""

    X = (
        training_frame
        .loc[:, feature_columns]
        .astype(float)
    )
    y = (
        training_frame["target_sales"]
        .astype(float)
    )

    splitter = TimeSeriesSplit(
        n_splits=N_SPLITS,
        test_size=TEST_SIZE,
    )

    fold_results: list[dict] = []

    for fold_number, (
        train_indices,
        test_indices,
    ) in enumerate(
        splitter.split(X),
        start=1,
    ):
        X_train = X.iloc[train_indices]
        X_test = X.iloc[test_indices]
        y_train = y.iloc[train_indices]
        y_test = y.iloc[test_indices]

        model = create_model(model_name)
        model.fit(X_train, y_train)

        validate_experiment_feature_names(
            model,
            feature_columns,
        )

        predictions = pd.Series(
            model.predict(X_test),
            index=y_test.index,
            name="Forecast",
        )

        metrics = calculate_metrics(
            y_test,
            predictions,
        )

        fold_results.append(
            {
                "model": model_name,
                "feature_set": feature_set_name,
                "feature_count": len(feature_columns),
                "fold": fold_number,
                "training_rows": len(X_train),
                "test_rows": len(X_test),
                "train_start": (
                    X_train.index.min()
                    .date()
                    .isoformat()
                ),
                "train_end": (
                    X_train.index.max()
                    .date()
                    .isoformat()
                ),
                "test_start": (
                    X_test.index.min()
                    .date()
                    .isoformat()
                ),
                "test_end": (
                    X_test.index.max()
                    .date()
                    .isoformat()
                ),
                "rmse": metrics["RMSE"],
                "mae": metrics["MAE"],
                "mape": metrics["MAPE"],
                "smape": metrics["sMAPE"],
            }
        )

    return fold_results


def build_summary(
    fold_results: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate mean and standard deviation metrics."""

    return (
        fold_results
        .groupby(
            [
                "model",
                "feature_set",
                "feature_count",
            ],
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


def build_fold_wins(
    fold_results: pd.DataFrame,
) -> pd.DataFrame:
    """Count which feature set performs better in each fold."""

    rows: list[dict] = []

    for model_name in sorted(
        fold_results["model"].unique()
    ):
        model_results = fold_results[
            fold_results["model"] == model_name
        ]

        for metric in ("rmse", "smape"):
            pivot = model_results.pivot(
                index="fold",
                columns="feature_set",
                values=metric,
            )

            six_better = int(
                (
                    pivot["six_features"]
                    < pivot["five_features"]
                ).sum()
            )

            five_better = int(
                (
                    pivot["five_features"]
                    < pivot["six_features"]
                ).sum()
            )

            ties = int(
                (
                    pivot["five_features"]
                    == pivot["six_features"]
                ).sum()
            )

            rows.append(
                {
                    "model": model_name,
                    "metric": metric,
                    "six_feature_wins": six_better,
                    "five_feature_wins": five_better,
                    "ties": ties,
                    "folds": len(pivot),
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    print(
        "[SOURCE] Loading BigQuery "
        "mart_forecast_training..."
    )

    training_frame = validate_training_frame(
        load_forecast_training()
    ).sort_index()

    print(
        f"[DATA] rows={len(training_frame)}, "
        f"start={training_frame.index.min().date()}, "
        f"end={training_frame.index.max().date()}"
    )

    print(
        "[FEATURES] five:",
        ", ".join(FIVE_FEATURES),
    )
    print(
        "[FEATURES] six:",
        ", ".join(SIX_FEATURES),
    )

    model_names = ["rf"]

    if HAS_XGBOOST:
        model_names.append("xgb")
    else:
        print(
            "[WARN] XGBoost is unavailable; "
            "only Random Forest will run."
        )

    all_results: list[dict] = []

    for model_name in model_names:
        for (
            feature_set_name,
            feature_columns,
        ) in FEATURE_SETS.items():
            print(
                f"[RUN] model={model_name}, "
                f"feature_set={feature_set_name}"
            )

            all_results.extend(
                evaluate_configuration(
                    training_frame=training_frame,
                    feature_set_name=feature_set_name,
                    feature_columns=feature_columns,
                    model_name=model_name,
                )
            )

    fold_results = pd.DataFrame(all_results)
    summary = build_summary(fold_results)
    fold_wins = build_fold_wins(fold_results)

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    folds_path = (
        REPORTS_DIR
        / "feature_set_comparison_folds.csv"
    )
    summary_path = (
        REPORTS_DIR
        / "feature_set_comparison_summary.csv"
    )
    wins_path = (
        REPORTS_DIR
        / "feature_set_comparison_wins.csv"
    )

    fold_results.to_csv(
        folds_path,
        index=False,
    )
    summary.to_csv(
        summary_path,
        index=False,
    )
    fold_wins.to_csv(
        wins_path,
        index=False,
    )

    print("\n=== FEATURE SET COMPARISON ===")
    print(
        summary.to_string(
            index=False,
            float_format=lambda value: f"{value:,.3f}",
        )
    )

    print("\n=== FOLD WINS ===")
    print(
        fold_wins.to_string(
            index=False,
        )
    )

    print(f"\n[OK] Fold results: {folds_path}")
    print(f"[OK] Summary:      {summary_path}")
    print(f"[OK] Fold wins:    {wins_path}")


if __name__ == "__main__":
    main()
