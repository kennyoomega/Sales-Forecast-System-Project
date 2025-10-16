# src/api_v1_5.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from typing import Literal, List, Tuple
from pathlib import Path
from datetime import datetime
import os
import joblib
import numpy as np

from src.db import SessionLocal, ForecastLog, init_db

app = FastAPI(title="Sales Forecast API v1.5 (with DB logging)")

# ---- Startup: create tables ----
@app.on_event("startup")
def _startup():
    init_db()

# ---- CORS (env-driven) ----
origins_env = os.getenv("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
allow_origin_regex = os.getenv("CORS_ORIGIN_REGEX")

print("[CORS] allow_origins =", allow_origins)
print("[CORS] allow_origin_regex =", allow_origin_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Model paths & cache ----
XGB_PATH = Path("reports/models/sales_forecast_xgb.pkl")
RF_PATH  = Path("reports/models/sales_forecast_rf.pkl")

AVAILABLE: dict[str, Path] = {}
if RF_PATH.exists():
    AVAILABLE["rf"] = RF_PATH
if XGB_PATH.exists():
    AVAILABLE["xgb"] = XGB_PATH

_CACHE: dict[str, object] = {}

def _get_model(name: Literal["rf", "xgb"]) -> object:
    if name not in AVAILABLE:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found. Train v1.2 first.")
    if name not in _CACHE:
        _CACHE[name] = joblib.load(AVAILABLE[name])
    return _CACHE[name]

def _simple_baseline(l1: float, l2: float, l3: float) -> float:
    return 0.5 * l1 + 0.3 * l2 + 0.2 * l3

def _load_model_and_feature_names(name: Literal["rf","xgb"]) -> Tuple[object, List[str]]:
    est = _get_model(name)
    names: List[str] = []
    if hasattr(est, "feature_names_in_"):
        try:
            names = [str(x) for x in est.feature_names_in_.tolist()]
        except Exception:
            pass
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
    roll3 = (lag1 + lag2 + lag3) / 3.0
    roll6 = roll3
    derived = {
        "lag_1": lag1, "lag1": lag1, "l1": lag1,
        "lag_2": lag2, "lag2": lag2, "l2": lag2,
        "lag_3": lag3, "lag3": lag3, "l3": lag3,
        "month": float(month_val),
        "roll_mean_3": roll3, "roll_mean_6": roll6,
    }
    if not names:
        return np.array([[lag1, lag2, lag3]], dtype=float)
    row = [float(derived.get(str(col).lower(), 0.0)) for col in names]
    return np.array(row, dtype=float).reshape(1, -1)

# ---- Routes ----
@app.get("/", include_in_schema=False)
def root():
    return {"message": "Sales Forecast API v1.5 running", "available_models": list(AVAILABLE.keys())}

@app.head("/", include_in_schema=False)
def root_head():
    return PlainTextResponse("ok")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.7.0"}

@app.get("/models")
def list_models():
    return {"available_models": list(AVAILABLE.keys())}

@app.get("/predict")
def predict(
    lag1: float = Query(...),
    lag2: float = Query(...),
    lag3: float = Query(...),
    model: Literal["rf","xgb"] = Query("rf"),
    month: int = Query(None, ge=1, le=12)
):
    if not AVAILABLE:
        raise HTTPException(status_code=500, detail="No models available. Train v1.2 first.")
    if month is None:
        now = datetime.utcnow()
        month = (now.month % 12) + 1
    try:
        est, feat_names = _load_model_and_feature_names(model)
        X = _build_features_as_in_training(lag1, lag2, lag3, month, feat_names)
        yhat = float(est.predict(X)[0])
    except Exception:
        yhat = _simple_baseline(lag1, lag2, lag3)

    logged = False
    db = SessionLocal()
    try:
        rec = ForecastLog(model=model, lag1=lag1, lag2=lag2, lag3=lag3, prediction=yhat)
        db.add(rec)
        db.commit()
        logged = True
    except Exception:
        db.rollback()
    finally:
        db.close()

    return {"prediction": round(yhat, 2), "model": model, "used_month": month, "logged": logged}

@app.get("/logs/latest")
def latest_logs(limit: int = 10):
    db = SessionLocal()
    try:
        rows = (
            db.query(ForecastLog)
            .order_by(ForecastLog.id.desc())
            .limit(limit)
            .all()
        )
        return [
            dict(
                id=r.id, model=r.model, lag1=r.lag1, lag2=r.lag2, lag3=r.lag3,
                prediction=r.prediction, created_at=r.created_at.isoformat()
            )
            for r in rows
        ]
    finally:
        db.close()
