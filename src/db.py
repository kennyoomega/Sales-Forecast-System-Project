"""PostgreSQL persistence for forecast prediction logs."""

from __future__ import annotations

import os
from datetime import date, datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:admin@db:5432/superstore",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class ForecastLog(Base):
    """Persist one warehouse-driven monthly forecast."""

    __tablename__ = "forecast_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    model: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    target_month: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    lag_1: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    lag_2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    lag_3: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    month_of_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    rolling_mean_3: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rolling_mean_6: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    prediction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


def init_db() -> None:
    """Create database tables that do not yet exist."""

    Base.metadata.create_all(bind=engine)
