# src/db.py
from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Read .env / system environment variables

DATABASE_URL = os.getenv("DATABASE_URL")
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
    model = Column(String(20), index=True)
    lag1 = Column(Float)
    lag2 = Column(Float)
    lag3 = Column(Float)
    prediction = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

def init_db():
    Base.metadata.create_all(bind=engine)
