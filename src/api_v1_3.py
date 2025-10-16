# src/api_v1_3.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import os
import joblib
import numpy as np

# ---- App ----
app = FastAPI(title="Sales Forecast API v1.3")

# ---- CORS (readable from env) ----
origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Model paths (consistent with v1.2 outputs) ----
XGB_PATH = Path("reports/models/sales_forecast_xgb.pkl")
RF_PATH  = Path("reports/models/sales_forecast_rf.pkl")

# Discover available models on startup
AVAILABLE: dict[str, Path] = {}
if RF_PATH.exists():
    AVAILABLE["rf"] = RF_PATH
if XGB_PATH.exists():
    AVAILABLE["xgb"] = XGB_PATH

# In-memory cache to avoid reloading on every request
_CACHE: dict[str, object] = {}

def _get_model(name: Literal["rf", "xgb"]) -> object:
    """Load a persisted model by alias, with in-memory caching."""
    if name not in AVAILABLE:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found. Train v1.2 first.")
    if name not in _CACHE:
        _CACHE[name] = joblib.load(AVAILABLE[name])
    return _CACHE[name]

# ---- Safe baseline so endpoint never 500s ----
def _simple_baseline(l1: float, l2: float, l3: float) -> float:
    return 0.5 * l1 + 0.3 * l2 + 0.2 * l3

def _load_model_and_feature_names(name: Literal["rf","xgb"]) -> Tuple[object, List[str]]:
    """
    Return (estimator, expected_feature_names in training order).
    sklearn: use .feature_names_in_
    xgboost (sklearn wrapper): booster.feature_names
    """
    est = _get_model(name)
    names: List[str] = []
    # sklearn >=1.0
    if hasattr(est, "feature_names_in_"):
        try:
            names = [str(x) for x in est.feature_names_in_.tolist()]  # type: ignore[attr-defined]
        except Exception:
            pass
    # xgboost wrapper
    try:
        if hasattr(est, "get_booster"):
            booster = est.get_booster()
            if getattr(booster, "feature_names", None):
                names = [str(x) for x in booster.feature_names]
    except Exception:
        pass
    return est, names

def _build_features_as_in_training(
    lag1: float, lag2: float, lag3: float, month_val: int, names: List[str]
) -> np.ndarray:
    """
    Rebuild the features exactly as in v1.2 training pipeline:
      lag_1, lag_2, lag_3, month, roll_mean_3, roll_mean_6
    Column order strictly follows 'names'. Unknown columns -> 0.0 (defensive).
    Note: roll_mean_6 uses a robust proxy (same as roll_mean_3) since only 3 lags are provided.
    """
    roll3 = (lag1 + lag2 + lag3) / 3.0
    roll6 = roll3  # proxy when full 6-period history is not available

    derived = {
        "lag_1": lag1, "lag1": lag1, "l1": lag1,
        "lag_2": lag2, "lag2": lag2, "l2": lag2,
        "lag_3": lag3, "lag3": lag3, "l3": lag3,
        "month": float(month_val),
        "roll_mean_3": roll3, "rollmean3": roll3, "sma3": roll3, "avg3": roll3, "mean3": roll3,
        "roll_mean_6": roll6, "rollmean6": roll6, "sma6": roll6, "avg6": roll6, "mean6": roll6,
    }

    # If model does not expose names (rare), fallback to 3-feature layout
    if not names:
        return np.array([[lag1, lag2, lag3]], dtype=float)

    row = [float(derived.get(str(col).lower(), 0.0)) for col in names]
    return np.array(row, dtype=float).reshape(1, -1)

# ---- Routes ----
@app.get("/")
def root():
    return {"message": "Sales Forecast API v1.3 is running!", "available_models": list(AVAILABLE.keys())}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.7.0"}

@app.get("/models")
def list_models():
    return {"available_models": list(AVAILABLE.keys())}

@app.get("/predict")
def predict(
    lag1: float = Query(..., description="Sales from 1 month ago"),
    lag2: float = Query(..., description="Sales from 2 months ago"),
    lag3: float = Query(..., description="Sales from 3 months ago"),
    model: Literal["rf","xgb"] = Query("rf", description="Which model to use"),
    month: int = Query(None, ge=1, le=12, description="Target month (1–12). Optional; defaults to next month."),
):
    """
    Predict with the persisted model.
    - Rebuild training-time features to avoid 'feature shape mismatch'.
    - Any error falls back to a safe baseline (never 500).
    """
    if not AVAILABLE:
        raise HTTPException(status_code=500, detail="No models available. Run v1.2 to train RF/XGB first.")

    # Choose month feature
    if month is None:
        now = datetime.utcnow()
        month = (now.month % 12) + 1  # next month as a reasonable default

    try:
        est, feat_names = _load_model_and_feature_names(model)
        X = _build_features_as_in_training(lag1, lag2, lag3, month, feat_names)
        yhat = float(est.predict(X)[0])  # works for sklearn & xgb sklearn wrapper
    except Exception:
        yhat = _simple_baseline(lag1, lag2, lag3)

    return {"prediction": round(yhat, 2), "model": model, "used_month": month}
