# src/api_v1_5.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from pathlib import Path
import joblib

from src.db import SessionLocal, ForecastLog  # ← DB session + table model

app = FastAPI(title="Sales Forecast API v1.5 (with DB logging)")

# --- CORS: allow local frontend access ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model paths ---
XGB_PATH = Path("reports/models/sales_forecast_xgb.pkl")
RF_PATH  = Path("reports/models/sales_forecast_rf.pkl")

AVAILABLE: dict[str, Path] = {}
if RF_PATH.exists():  AVAILABLE["rf"]  = RF_PATH
if XGB_PATH.exists(): AVAILABLE["xgb"] = XGB_PATH

_CACHE: dict[str, object] = {}
def get_model(name: Literal["rf","xgb"]):
    if name not in AVAILABLE:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found. Train v1.2 first.")
    if name not in _CACHE:
        _CACHE[name] = joblib.load(AVAILABLE[name])
    return _CACHE[name]

@app.get("/")
def root():
    return {"message": "v1.5 running", "available_models": list(AVAILABLE.keys())}

@app.get("/models")
def list_models():
    return {"available_models": list(AVAILABLE.keys())}

@app.get("/predict")
def predict(
    lag1: float = Query(..., description="Sales from 1 month ago"),
    lag2: float = Query(..., description="Sales from 2 months ago"),
    lag3: float = Query(..., description="Sales from 3 months ago"),
    model: Literal["rf","xgb"] = Query("rf", description="Which model to use"),
):
    if not AVAILABLE:
        raise HTTPException(status_code=500, detail="No models available. Run v1.2 to train RF/XGB first.")
    m = get_model(model)
    yhat = float(m.predict([[lag1, lag2, lag3]])[0])

    # --- Log to PostgreSQL (errors do not block response) ---
    logged = False
    db = SessionLocal()
    try:
        rec = ForecastLog(model=model, lag1=lag1, lag2=lag2, lag3=lag3, prediction=yhat)
        db.add(rec)
        db.commit()
        logged = True
    except Exception:
        # In production: use proper logging (warning/error)
        db.rollback()
    finally:
        db.close()

    return {"prediction": round(yhat, 2), "model": model, "logged": logged}

# --- Convenience: view latest N logs ---
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
