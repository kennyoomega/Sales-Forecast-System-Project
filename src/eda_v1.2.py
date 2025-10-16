#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDA v1.2 — Monthly Forecast + Seasonal-Naive Baseline + Metrics & Report
Author: Siyu (with your AI partner)
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import matplotlib.pyplot as plt

# ---- Optional: XGBoost ----
try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False


# =========================
# Utilities & Metrics
# =========================
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denom = (np.abs(y_true) + np.abs(y_pred))
    denom[denom == 0] = 1e-8
    return float(100.0 * np.mean(2.0 * np.abs(y_pred - y_true) / denom))

try:
    from sklearn.metrics import root_mean_squared_error as _rmse
    def rmse(y_true, y_pred):
        return float(_rmse(y_true, y_pred))
except Exception:
    from sklearn.metrics import mean_squared_error
    def rmse(y_true, y_pred):
        return float(np.sqrt(mean_squared_error(y_true, y_pred)))



# =========================
# Data preparation
# =========================
def load_and_monthly_aggregate(csv_path: Path,
                               date_col: str = "date",
                               target_col: str = "Sales",
                               freq: str = "MS",
                               encoding: str = "utf-8",
                               sep: str = ",") -> pd.Series:
    """
    Load CSV, parse date, monthly aggregate to a univariate series ts['Sales'].
    If multiple stores/skus exist, it aggregates all; you can filter upstream if needed.
    """
    # Try given encoding first, then common fallbacks if needed
    tried = []
    def _try_read(enc: str):
        return pd.read_csv(csv_path, encoding=enc, sep=sep)

    df = None
    for enc in [encoding, "cp1252", "latin1", "ISO-8859-1"]:
        if enc in tried: 
            continue
        try:
            df = _try_read(enc)
            break
        except UnicodeDecodeError:
            tried.append(enc)
            df = None

    if df is None:
        # last resort: raise using the original encoding attempt
        df = pd.read_csv(csv_path, encoding=encoding, sep=sep)

    cols_preview = list(df.columns)[:10]

    if date_col not in df.columns:
        raise ValueError(
            f"CSV missing required date column: '{date_col}'. "
            f"Got columns (first 10): {cols_preview}. "
            f"Tip: many Superstore files use 'Order Date'."
        )
    if target_col not in df.columns:
        raise ValueError(
            f"CSV missing required target column: '{target_col}'. "
            f"Got columns (first 10): {cols_preview}."
        )

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.sort_values(date_col)

    # Monthly aggregate
    ts = (
        df.set_index(date_col)[target_col]
          .resample(freq)  # 'MS' → Month Start
          .sum()
          .astype(float)
    )
    ts = ts.dropna()
    return ts


def add_lag_features(ts: pd.Series, n_lags: int = 3) -> pd.DataFrame:
    """Create lag features for a univariate monthly series."""
    df = pd.DataFrame({"Sales": ts})
    for i in range(1, n_lags + 1):
        df[f"lag_{i}"] = df["Sales"].shift(i)
    # calendar features (month)
    df["month"] = df.index.month
    # rolling features (robust)
    df["roll_mean_3"] = df["Sales"].shift(1).rolling(3, min_periods=1).mean()
    df["roll_mean_6"] = df["Sales"].shift(1).rolling(6, min_periods=1).mean()
    df = df.dropna()  # drop rows that cannot form lags
    return df


@dataclass
class SplitData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def split_train_test(df_feat: pd.DataFrame, horizon: int = 3) -> SplitData:
    """Time-aware split: last 'horizon' months as test."""
    if horizon <= 0:
        raise ValueError("horizon must be >= 1")
    y = df_feat["Sales"].copy()
    X = df_feat.drop(columns=["Sales"])
    X_train, X_test = X.iloc[:-horizon, :], X.iloc[-horizon:, :]
    y_train, y_test = y.iloc[:-horizon], y.iloc[-horizon:]
    return SplitData(X_train, X_test, y_train, y_test)


# =========================
# Models
# =========================
def train_rf(X_train, y_train) -> RandomForestRegressor:
    model = RandomForestRegressor(
        n_estimators=600,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model

def train_xgb(X_train, y_train) -> "XGBRegressor":
    model = XGBRegressor(
        n_estimators=600,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        tree_method="hist",
    )
    model.fit(X_train, y_train)
    return model


# =========================
# Training + Baseline
# =========================
def train_forecast_model(ts: pd.Series,
                         model_path: Path,
                         model_name: str = "rf",
                         horizon: int = 3):
    """
    Train model and build seasonal-naive baseline for the same hold-out period.
    Returns: (fitted_model, test_df[Actual, Forecast, Baseline])
    """
    df_feat = add_lag_features(ts, n_lags=3)
    sp = split_train_test(df_feat, horizon=horizon)
    if model_name == "xgb":
        if not _HAS_XGB:
            raise RuntimeError("XGBoost not installed. pip install xgboost")
        model = train_xgb(sp.X_train, sp.y_train)
    else:
        model = train_rf(sp.X_train, sp.y_train)

    preds = model.predict(sp.X_test)
    joblib.dump(model, model_path)

    # test frame
    test_df = pd.DataFrame(
        {"Actual": sp.y_test, "Forecast": preds},
        index=sp.y_test.index
    )

    # Seasonal-naive baseline: last year same month, fallback to previous month
    last_year = ts.shift(12).reindex(test_df.index)
    prev_month = ts.shift(1).reindex(test_df.index)
    baseline = last_year.fillna(prev_month)
    test_df["Baseline"] = baseline

    return model, test_df


# =========================
# Plot & Report
# =========================
def plot_forecast(full_ts: pd.Series,
                  test_df: pd.DataFrame,
                  figs_dir: Path) -> str:
    ensure_dir(figs_dir)
    fig_path = figs_dir / "forecast_vs_actual.png"

    plt.figure(figsize=(10, 5))
    # history
    cutoff = test_df.index.min()
    plt.plot(full_ts[full_ts.index < cutoff], label="History (Actual)", linewidth=2)
    # hold-out actual & preds
    plt.plot(test_df.index, test_df["Actual"], label="Hold-out Actual", linestyle="--", linewidth=2)
    plt.plot(test_df.index, test_df["Forecast"], label="Model Forecast", linewidth=2)
    plt.plot(test_df.index, test_df["Baseline"], label="Seasonal-Naive Baseline", linewidth=2)
    plt.title("Actual vs Forecast (Model vs Seasonal-Naive)")
    plt.xlabel("Date (Monthly)")
    plt.ylabel("Sales")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    return str(fig_path)


def write_html_report(outdir: Path,
                      title: str,
                      forecast_fig: str,
                      flags: dict,
                      metrics: dict) -> str:
    html = outdir / "eda_report_1_2.html"
    css = """<style>
    body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;}
    h1{margin-bottom:8px;}
    .meta{color:#666;margin-bottom:16px;}
    .fig{margin:18px 0;}
    img{max-width:100%;height:auto;border:1px solid #eee;border-radius:8px;}
    table{border-collapse:collapse;margin:12px 0;}
    th,td{border:1px solid #e5e7eb;padding:6px 10px;text-align:right;}
    th:first-child,td:first-child{text-align:left;}
    pre{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto;}
    </style>"""

    def fmt(x):
        try:
            if isinstance(x, float):
                return f"{x:,.2f}"
            return f"{x}"
        except:
            return str(x)

    # Metrics table
    metrics_html = ""
    if metrics:
        rows = []
        for k in ["MAPE", "sMAPE", "MAE", "RMSE"]:
            rows.append(f"<tr><td>{k}</td><td>{fmt(metrics['Baseline'].get(k))}</td><td>{fmt(metrics['Model'].get(k))}</td></tr>")
        metrics_html = f"""
        <h2>Evaluation Metrics</h2>
        <table>
          <tr><th>Metric</th><th>Baseline</th><th>Model</th></tr>
          {''.join(rows)}
        </table>
        """

    with html.open("w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body>")
        f.write(f"<h1>{title}</h1>")
        f.write(f"<div class='meta'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>")
        f.write("<h2>Forecast vs Actual</h2>")
        f.write(f'<div class="fig"><img src="figures/{Path(forecast_fig).name}" /></div>')
        f.write(metrics_html)
        f.write("<h2>Run Config</h2>")
        f.write(f"<pre>{json.dumps(flags, indent=2)}</pre>")
        f.write("</body></html>")
    return str(html)


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(description="EDA v1.2 Monthly Forecast with Baseline & Metrics")
    parser.add_argument("--input", type=str, required=True, help="Path to input CSV (must contain date & Sales)")
    parser.add_argument("--date_col", type=str, default="date", help="Date column name (e.g., 'Order Date')")
    parser.add_argument("--target_col", type=str, default="Sales", help="Target column name (e.g., 'Sales')")
    parser.add_argument("--outdir", type=str, default="reports", help="Output directory")
    parser.add_argument("--model", type=str, default="rf", choices=["rf", "xgb"], help="Model: rf or xgb")
    parser.add_argument("--horizon", type=int, default=3, help="Hold-out horizon months")
    parser.add_argument("--title", type=str, default="Sales Forecast v1.2 — Monthly", help="Report title")
    parser.add_argument("--encoding", type=str, default="utf-8", help="CSV encoding, e.g. utf-8 / cp1252 / latin1")
    parser.add_argument("--sep", type=str, default=",", help="CSV delimiter, e.g. , or ;")
    args = parser.parse_args()

    outdir = ensure_dir(Path(args.outdir))
    figs_dir = ensure_dir(outdir / "figures")
    models_dir = ensure_dir(outdir / "models")

    # 1) Load & aggregate monthly
    ts = load_and_monthly_aggregate(
        Path(args.input),
        args.date_col,
        args.target_col,
        freq="MS",
        encoding=args.encoding,
        sep=args.sep
    )
    if len(ts) < args.horizon + 15:
        raise RuntimeError(f"Time series too short ({len(ts)} points). Need >= horizon+15.")

    # 2) Train & build baseline
    model_path = models_dir / f"sales_forecast_{args.model}.pkl"
    model, test_df = train_forecast_model(ts, model_path, model_name=args.model, horizon=args.horizon)

    # 3) Metrics (Baseline vs Model)
    y_true = test_df["Actual"]
    y_hat  = test_df["Forecast"]
    y_base = test_df["Baseline"]

    metrics = {
        "Baseline": {
            "MAPE": mape(y_true, y_base),
            "sMAPE": smape(y_true, y_base),
            "MAE":  float(mean_absolute_error(y_true, y_base)),
            "RMSE": rmse(y_true, y_base),
        },
        "Model": {
            "MAPE": mape(y_true, y_hat),
            "sMAPE": smape(y_true, y_hat),
            "MAE":  float(mean_absolute_error(y_true, y_hat)),
            "RMSE": rmse(y_true, y_hat),
        },
    }

    impr_mape_pct = None
    if np.isfinite(metrics["Baseline"]["MAPE"]) and np.isfinite(metrics["Model"]["MAPE"]):
        b, m = metrics["Baseline"]["MAPE"], metrics["Model"]["MAPE"]
        if b > 0:
            impr_mape_pct = (b - m) / b * 100.0

    print("[METRICS] Baseline:", metrics["Baseline"])
    print("[METRICS] Model   :", metrics["Model"])
    if impr_mape_pct is not None:
        print(f"[METRICS] Improvement on MAPE: {impr_mape_pct:.1f}%")
    else:
        print("[METRICS] Improvement on MAPE: n/a")

    # 4) Plot
    forecast_fig = plot_forecast(ts, test_df, figs_dir)

    # 5) Report
    flags = {
        "model": "XGBoost" if args.model == "xgb" else "RandomForest",
        "lags": 3,
        "horizon": int(args.horizon),
        "points_total": int(len(ts)),
        "freq": "MS",
        "encoding": args.encoding,
        "sep": args.sep,
        "date_col": args.date_col,
        "target_col": args.target_col,
    }
    report_path = write_html_report(outdir, args.title, forecast_fig, flags, metrics)
    print(f"[OK] Report: {report_path}")
    print(f"[OK] Model saved: {model_path}")

if __name__ == "__main__":
    main()
