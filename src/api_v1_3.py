from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from pathlib import Path
import joblib

app = FastAPI(title="Sales Forecast API v1.3")

# --- CORS: Allow local frontend access ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model Path ---
XGB_PATH = Path("reports/models/sales_forecast_xgb.pkl")
RF_PATH  = Path("reports/models/sales_forecast_rf.pkl")

# Record available models (even if only one works)
AVAILABLE: dict[str, Path] = {}
if RF_PATH.exists():  AVAILABLE["rf"]  = RF_PATH
if XGB_PATH.exists(): AVAILABLE["xgb"] = XGB_PATH

# Cached loaded models to avoid redundant loading
_CACHE: dict[str, object] = {}

def get_model(name: Literal["rf","xgb"]) -> object:
    if name not in AVAILABLE:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found. Train v1.2 first.")
    if name not in _CACHE:
        _CACHE[name] = joblib.load(AVAILABLE[name])
    return _CACHE[name]

@app.get("/")
def root():
    return {
        "message": "Sales Forecast API v1.3 is running!",
        "available_models": list(AVAILABLE.keys())
    }

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
    return {"prediction": round(yhat, 2), "model": model}
