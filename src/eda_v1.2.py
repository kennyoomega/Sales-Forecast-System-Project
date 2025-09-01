"""
Retail EDA + Forecasting v1.2
Adds: monthly aggregate, lag features, RF/XGBoost forecasting (switchable),
Actual vs Forecast chart, and model persistence.
"""

import argparse, json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
import joblib

# try xgboost lazily (optional)
try:
    import xgboost as xgb
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False


# ---------------- utils ----------------

def ensure_outdirs(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    figs = outdir / "figures"; figs.mkdir(parents=True, exist_ok=True)
    models = outdir / "models"; models.mkdir(parents=True, exist_ok=True)
    return figs, models

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    lower = {c.lower(): c for c in df.columns}
    for key in ["order date","order_date","orderdate"]:
        if key in lower:
            df.rename(columns={lower[key]: "Order Date"}, inplace=True)
            break
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    return df

def monthly_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    if "Order Date" not in df.columns or "Sales" not in df.columns:
        raise ValueError("Order Date / Sales required")
    ts = df.dropna(subset=["Order Date"]).set_index("Order Date")["Sales"].resample("MS").sum()
    return ts.to_frame("Sales")

def add_lag_features(ts_df: pd.DataFrame, n_lags=3) -> pd.DataFrame:
    df = ts_df.copy()
    for i in range(1, n_lags + 1):
        df[f"lag_{i}"] = df["Sales"].shift(i)
    return df.dropna()

def split_train_test(df_features: pd.DataFrame, horizon=3):
    X = df_features.drop("Sales", axis=1)
    y = df_features["Sales"]
    train_size = max(1, len(df_features) - horizon)
    return X.iloc[:train_size], X.iloc[train_size:], y.iloc[:train_size], y.iloc[train_size:]


# ---------------- modeling ----------------

def train_rf(X_train, y_train, n_estimators=300, random_state=42):
    model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
    model.fit(X_train, y_train)
    return model

def train_xgb(X_train, y_train, random_state=42):
    params = dict(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=random_state,
        tree_method="hist",
    )
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train)
    return model

def train_forecast_model(ts_df: pd.DataFrame, model_path: Path, model_name="rf", horizon=3):
    df_feat = add_lag_features(ts_df, n_lags=3)
    X_train, X_test, y_train, y_test = split_train_test(df_feat, horizon=horizon)

    if model_name == "xgb":
        if not _HAS_XGB:
            raise RuntimeError("XGBoost is not installed. Run: pip install xgboost")
        model = train_xgb(X_train, y_train)
    else:
        model = train_rf(X_train, y_train)

    preds = model.predict(X_test)
    joblib.dump(model, model_path)

    test_df = pd.DataFrame({"Actual": y_test, "Forecast": preds}, index=y_test.index)
    return model, test_df


# ---------------- plots ----------------

def plot_forecast(ts_df: pd.DataFrame, test_df: pd.DataFrame, figs_dir: Path, dpi=120):
    plt.figure(figsize=(10,5), dpi=dpi)
    plt.plot(ts_df.index, ts_df["Sales"], label="Actual (all data)")
    plt.plot(test_df.index, test_df["Actual"], label="Actual (test)", marker="o")
    plt.plot(test_df.index, test_df["Forecast"], label="Forecast", marker="x")
    plt.title("Actual vs Forecast (monthly)")
    plt.xlabel("Month"); plt.ylabel("Sales")
    plt.legend(); plt.tight_layout()
    path = figs_dir / "forecast_vs_actual.png"
    plt.savefig(path); plt.close()
    return str(path)


# ---------------- report ----------------

def write_html_report(outdir: Path, title: str, forecast_fig: str, flags: dict):
    html = outdir / "eda_report_1_2.html"
    css = """<style>body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;}
    h1{margin-bottom:8px;}.meta{color:#666;margin-bottom:16px;}
    .fig{margin:18px 0;}img{max-width:100%;height:auto;border:1px solid #eee;border-radius:8px;}
    pre{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto;}</style>"""
    with html.open("w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body>")
        f.write(f"<h1>{title}</h1>")
        f.write(f"<div class='meta'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>")
        f.write("<h2>Forecast vs Actual</h2>")
        f.write(f'<div class="fig"><img src="figures/{Path(forecast_fig).name}" /></div>')
        f.write("<h2>Run Config</h2>")
        f.write(f"<pre>{json.dumps(flags, indent=2)}</pre>")
        f.write("</body></html>")
    return str(html)


# ---------------- main ----------------

def main():
    p = argparse.ArgumentParser(description="Retail EDA + Forecasting v1.2")
    p.add_argument("--input", required=True, help="Path to Superstore.csv")
    p.add_argument("--outdir", default="reports", help="Output directory")
    p.add_argument("--title", default="Retail EDA — MVP 1.2")
    p.add_argument("--model", choices=["rf","xgb"], default="rf", help="Forecast model to use")
    p.add_argument("--horizon", type=int, default=3, help="Test horizon (last N months)")
    args = p.parse_args()

    in_path = Path(args.input)
    outdir = Path(args.outdir)
    figs_dir, models_dir = ensure_outdirs(outdir)

    # Load & aggregate (latin1 for Windows/Excel-safe; try utf-8 first)
    try:
        df = pd.read_csv(in_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(in_path, encoding="latin1", low_memory=False)
    df = normalise_columns(df)
    ts_df = monthly_aggregate(df)

    # Train model
    model_path = models_dir / f"sales_forecast_{args.model}.pkl"
    model, test_df = train_forecast_model(ts_df, model_path, model_name=args.model, horizon=args.horizon)

    # Plot
    forecast_fig = plot_forecast(ts_df, test_df, figs_dir)

    # Report
    flags = {"model": "XGBoost" if args.model=="xgb" else "RandomForest",
             "lags": 3, "horizon": int(args.horizon), "points_total": int(len(ts_df))}
    report_path = write_html_report(outdir, args.title, forecast_fig, flags)
    print(f"[OK] Report: {report_path}")
    print(f"[OK] Model saved: {model_path}")

if __name__ == "__main__":
    main()
