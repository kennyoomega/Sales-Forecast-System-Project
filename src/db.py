# src/db.py
from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()  # optional in docker, safe locally

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:admin@db:5432/superstore")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Example:\n"
        "postgresql+psycopg2://postgres:123456@localhost:5432/salesdb"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class ForecastLog(Base):
    __tablename__ = "forecast_logs"
    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(20), index=True, nullable=False)
    lag1 = Column(Float, nullable=False)
    lag2 = Column(Float, nullable=False)
    lag3 = Column(Float, nullable=False)
    prediction = Column(Float, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

def init_db():
    """Create tables if they do not exist (idempotent)."""
    Base.metadata.create_all(bind=engine)
