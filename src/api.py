"""FastAPI application for warehouse-driven sales forecasting."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.bq_client import (
    load_next_month_features,
    query_mart,
)
from src.db import ForecastLog, SessionLocal, init_db
from src.feature_contract import (
    FEATURE_COLUMNS,
    FeatureContractError,
    validate_model_feature_names,
    validate_prediction_frame,
)


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATHS: dict[str, Path] = {
    "rf": ROOT_DIR / "reports" / "models" / "sales_forecast_rf.pkl",
    "xgb": ROOT_DIR / "reports" / "models" / "sales_forecast_xgb.pkl",
}

MODEL_CACHE: dict[str, object] = {}


def available_models() -> list[str]:
    """Return model names whose artifact files exist."""

    return [
        name
        for name, path in MODEL_PATHS.items()
        if path.is_file()
    ]


def get_model(
    model_name: Literal["rf", "xgb"],
) -> object:
    """Load and validate one model artifact, caching it afterward."""

    model_path = MODEL_PATHS[model_name]

    if not model_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Model '{model_name}' is unavailable. "
                "Run src.train_forecast first."
            ),
        )

    if model_name not in MODEL_CACHE:
        try:
            model = joblib.load(model_path)

            validate_model_feature_names(
                getattr(model, "feature_names_in_", None)
            )

            MODEL_CACHE[model_name] = model

        except FeatureContractError as exc:
            logger.exception(
                "Model feature contract validation failed for '%s'.",
                model_name,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Model '{model_name}' does not match "
                    "the current feature contract."
                ),
            ) from exc

        except Exception as exc:
            logger.exception(
                "Could not load model '%s'.",
                model_name,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Could not load model '{model_name}'.",
            ) from exc

    return MODEL_CACHE[model_name]


def serialize_value(value):
    """Convert warehouse and database scalar values for JSON output."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if hasattr(value, "item"):
        return value.item()

    return value


def serialize_rows(rows: list[dict]) -> list[dict]:
    """Normalize rows returned from BigQuery."""

    return [
        {
            key: serialize_value(value)
            for key, value in row.items()
        }
        for row in rows
    ]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize persistence before serving requests."""

    init_db()
    yield


app = FastAPI(
    title="Sales Forecast API",
    version="1.8.0",
    lifespan=lifespan,
)


origins_env = os.getenv("CORS_ORIGINS", "")
allow_origins = [
    origin.strip()
    for origin in origins_env.split(",")
    if origin.strip()
]
allow_origin_regex = os.getenv("CORS_ORIGIN_REGEX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Sales Forecast API running",
        "version": "1.8.0",
        "available_models": available_models(),
        "default_model": "rf",
    }


@app.head("/", include_in_schema=False)
def root_head():
    return PlainTextResponse("ok")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.8.0",
        "available_models": available_models(),
    }


@app.get("/models")
def list_models():
    return {
        "available_models": available_models(),
        "default_model": "rf",
    }


@app.get("/predict")
def predict(
    model: Literal["rf", "xgb"] = Query("rf"),
):
    """Forecast the next warehouse month using dbt-generated features."""

    estimator = get_model(model)

    try:
        feature_frame = validate_prediction_frame(
            load_next_month_features()
        )

    except FeatureContractError as exc:
        logger.exception(
            "Prediction feature contract validation failed."
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Warehouse prediction features do not match "
                "the required contract."
            ),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Could not load next-month features from BigQuery."
        )
        raise HTTPException(
            status_code=503,
            detail="Forecast features are unavailable.",
        ) from exc

    prediction_features = (
        feature_frame
        .loc[:, FEATURE_COLUMNS]
        .astype(float)
    )

    try:
        prediction = float(
            estimator.predict(prediction_features)[0]
        )

    except Exception as exc:
        logger.exception(
            "Prediction failed for model '%s'.",
            model,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed for model '{model}'.",
        ) from exc

    row = feature_frame.iloc[0]
    target_month = row["target_month"].date()

    log_record = ForecastLog(
        model=model,
        target_month=target_month,
        lag_1=float(row["lag_1"]),
        lag_2=float(row["lag_2"]),
        lag_3=float(row["lag_3"]),
        month_of_year=int(row["month_of_year"]),
        rolling_mean_3=float(row["rolling_mean_3"]),
        rolling_mean_6=float(row["rolling_mean_6"]),
        prediction=prediction,
    )

    logged = False
    database = SessionLocal()

    try:
        database.add(log_record)
        database.commit()
        database.refresh(log_record)
        logged = True

    except Exception:
        database.rollback()
        logger.exception(
            "Prediction succeeded but database logging failed."
        )

    finally:
        database.close()

    features = {
        column: serialize_value(row[column])
        for column in FEATURE_COLUMNS
    }

    return {
        "target_month": target_month.isoformat(),
        "prediction": round(prediction, 2),
        "model": model,
        "features": features,
        "feature_source": "mart_next_month_features",
        "logged": logged,
    }


@app.get("/logs/latest")
def latest_logs(
    limit: int = Query(10, ge=1, le=100),
):
    database = SessionLocal()

    try:
        records = (
            database
            .query(ForecastLog)
            .order_by(ForecastLog.id.desc())
            .limit(limit)
            .all()
        )

        rows = [
            {
                "id": record.id,
                "model": record.model,
                "target_month": record.target_month,
                "lag_1": record.lag_1,
                "lag_2": record.lag_2,
                "lag_3": record.lag_3,
                "month_of_year": record.month_of_year,
                "rolling_mean_3": record.rolling_mean_3,
                "rolling_mean_6": record.rolling_mean_6,
                "prediction": record.prediction,
                "created_at": record.created_at,
            }
            for record in records
        ]

        return jsonable_encoder(rows)

    finally:
        database.close()


@app.get("/analytics/monthly")
def analytics_monthly(
    limit: int = Query(48, ge=1, le=1000),
):
    try:
        rows = query_mart(
            "mart_monthly_sales",
            limit=limit,
        )
        return {
            "data": serialize_rows(rows),
            "source": "bigquery_mart",
        }

    except Exception as exc:
        logger.exception(
            "Monthly analytics mart query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Monthly analytics data is unavailable.",
        ) from exc


@app.get("/analytics/category")
def analytics_category():
    try:
        rows = query_mart(
            "mart_sales_by_category"
        )
        return {
            "data": serialize_rows(rows),
            "source": "bigquery_mart",
        }

    except Exception as exc:
        logger.exception(
            "Category analytics mart query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Category analytics data is unavailable.",
        ) from exc


@app.get("/analytics/region")
def analytics_region():
    try:
        rows = query_mart(
            "mart_sales_by_region"
        )
        return {
            "data": serialize_rows(rows),
            "source": "bigquery_mart",
        }

    except Exception as exc:
        logger.exception(
            "Region analytics mart query failed."
        )
        raise HTTPException(
            status_code=503,
            detail="Region analytics data is unavailable.",
        ) from exc
