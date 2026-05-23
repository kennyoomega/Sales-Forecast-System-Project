# 🚀 Sales Forecast & Analytics Platform (v1.8 — dbt + BigQuery Analytics Layer)

A full-stack retail analytics and forecasting platform built on **FastAPI**, **PostgreSQL**, and **Next.js**, fully containerized with **Docker** and deployed across **Render**, **Vercel**, and **Neon Cloud**.

The system delivers end-to-end analytics from raw data ingestion to machine learning forecasts, cloud APIs, interactive dashboards, and a production-grade **dbt + BigQuery analytics layer** with full data lineage, testing, and documentation.

---

## ✨ What's new in v1.8

### Compared with v1.7 (Docker + Cloud Deployment), this version adds a complete analytics engineering layer

- 🏗️ **dbt + BigQuery integration** — staging and mart models with full lineage tracking
- 🧪 **19 dbt tests** — uniqueness, not_null, and accepted_values across all models
- 📊 **5 mart models** — monthly sales, category, segment, region, and product performance
- 🔍 **Data lineage graph** — visual DAG from raw source to all downstream marts
- 📄 **Auto-generated documentation** — every model and column documented via dbt docs
- ⚙️ **Materialization strategy** — staging as views (always fresh), marts as tables (fast queries)

---

## 🏗️ Architecture Overview

```
Superstore.csv
    │
    ▼
BigQuery raw.superstore_orders          ← raw source, never touched
    │
    ▼
dbt staging: stg_superstore_orders      ← clean, rename, cast types
    │
    ├──► mart_monthly_sales             ← feeds FastAPI /predict (lag features pre-computed)
    ├──► mart_sales_by_category         ← Category + Sub-Category performance
    ├──► mart_sales_by_segment          ← Consumer / Corporate / Home Office
    ├──► mart_sales_by_region           ← East / West / Central / South
    └──► mart_product_performance       ← product ranking with window functions
    │
    ▼
FastAPI (Render) ←→ Next.js (Vercel) ←→ PostgreSQL (Neon)
    │
    ▼
Power BI Dashboards
```

---

## 🧩 Tech Stack

| Category | Technology | Description |
|---|---|---|
| **Frontend** | Next.js (React + TypeScript) | Forecast UI + logs table |
| **Backend** | FastAPI + SQLAlchemy | API endpoints + DB logging |
| **Database (OLTP)** | Neon PostgreSQL | Prediction logs, operational data |
| **Database (OLAP)** | BigQuery (GCP) | Analytics layer, dbt target |
| **Transformation** | dbt-bigquery | Staging + mart models, tests, lineage |
| **ML Models** | RandomForest / XGBoost | Trained forecasting models |
| **Visualization** | Power BI | KPI dashboards and insights |
| **Containerization** | Docker + Docker Compose | Unified local & cloud environment |
| **Deployment** | Render + Vercel | Cost-efficient public hosting |
| **Cloud compatibility** | Azure App Service + ACR | Fully portable enterprise-grade setup |

---

## 📊 dbt Analytics Layer

### Model Structure

```
models/
├── staging/
│   ├── stg_superstore_orders.sql    ← clean + rename raw data
│   └── schema.yml                   ← source definition + tests
└── marts/
    ├── mart_monthly_sales.sql        ← monthly aggregation + lag features
    ├── mart_sales_by_category.sql    ← category + sub-category performance
    ├── mart_sales_by_segment.sql     ← segment breakdown over time
    ├── mart_sales_by_region.sql      ← regional performance
    ├── mart_product_performance.sql  ← product ranking with RANK() OVER PARTITION BY
    └── schema.yml                    ← tests for all mart models
```

### Design Decisions

- **Staging as views** — cheap, always fresh, single source of truth for cleaning logic
- **Marts as tables** — fast reads for FastAPI and BI tools
- **All marts reference staging via `{{ ref() }}`** — never the raw table directly
- **19 tests** — uniqueness, not_null, accepted_values guard against silent data failures

### Key mart: mart_monthly_sales

Replaces the CSV-reading and pandas lag feature logic in `eda_v1.2.py`. Pre-computes `lag_1`, `lag_2`, `lag_3` in SQL using `LAG() OVER (ORDER BY month)` — the same logic as `df['Sales'].shift(1)` but persistent, testable, and queryable by any downstream consumer.

---

## ⚙️ Quickstart

### Local Development (Dockerized)

```bash
docker-compose up --build
```

- API → http://localhost:8000
- Frontend → http://localhost:3000
- PostgreSQL → containerized with persistent volume

### dbt + BigQuery

```bash
cd sales_forecast_dbt

# Run all models
dbt run

# Run all tests
dbt test

# Generate and serve documentation
dbt docs generate
dbt docs serve
```

---

## 🖥️ Live Demo

| Layer | Platform | URL |
|---|---|---|
| **Frontend (Next.js)** | Vercel | ✅ Live UI |
| **Backend (FastAPI)** | Render | ✅ Public API |
| **Database (PostgreSQL)** | Neon Cloud | Persistent data layer |

---

## 📂 Project Structure

```
.
├── sales_forecast_dbt/              ← dbt project (v1.8)
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_superstore_orders.sql
│   │   │   └── schema.yml
│   │   └── marts/
│   │       ├── mart_monthly_sales.sql
│   │       ├── mart_sales_by_category.sql
│   │       ├── mart_sales_by_segment.sql
│   │       ├── mart_sales_by_region.sql
│   │       ├── mart_product_performance.sql
│   │       └── schema.yml
│   └── dbt_project.yml
├── backend/
│   └── Dockerfile
├── data/                            ← Superstore.csv (not committed)
├── frontend/                        ← Next.js app
├── src/
│   ├── eda_v1.0.py                  ← EDA MVP
│   ├── eda_v1.1.py                  ← Enhanced EDA
│   ├── eda_v1.2.py                  ← Forecasting (RF/XGBoost)
│   ├── bq_client.py                 ← BigQuery connection utility
│   ├── api_v1_5.py                  ← FastAPI backend
│   └── db.py                        ← SQLAlchemy models
├── reports/
│   └── models/                      ← Saved .pkl files
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🗺️ Roadmap

- [x] **v1.0** — CSV normalisation → KPIs → HTML report
- [x] **v1.1** — Enhanced EDA: winsorisation, Top-N, geo, profit contribution
- [x] **v1.2** — Forecasting: RF/XGBoost, MAPE 24% → 11.5% (52% reduction)
- [x] **v1.3** — FastAPI: `/predict` endpoint
- [x] **v1.4** — Next.js frontend
- [x] **v1.5** — PostgreSQL: prediction logging
- [x] **v1.6** — Power BI dashboards
- [x] **v1.7** — Docker + cloud deployment (Render / Vercel / Neon)
- [x] **v1.8** — dbt + BigQuery: staging, 5 marts, 19 tests, lineage graph
- [ ] **v1.9** — Airflow orchestration: scheduled dbt runs

---

## Dataset & Licence

- Dataset: Kaggle *Sample Superstore* (public demo dataset)
- Intended for learning and portfolio use
- Licence: MIT

---

### 💬 Built with FastAPI, Next.js, PostgreSQL, Docker, dbt, and BigQuery — covering data engineering, analytics engineering, and cloud deployment end to end.
