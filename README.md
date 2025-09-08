# Sales Forecast System (v1.5 — FastAPI + Frontend + PostgreSQL Logging)

A full-stack retail analytics MVP built on Kaggle’s Superstore dataset.

**New in v1.5:** added PostgreSQL logging — every forecast request (model, lags, prediction) is now stored in a relational database for audit, monitoring, and future BI dashboards. 

Scope: Python EDA → forecasting → API → frontend → database logging → BI → Azure deployment.

---

## ✨ What’s new in v1.5

### Compared with v1.3/v1.4 (FastAPI + Frontend), this version v1.5 adds persistence
- 🗄️ PostgreSQL integration — requests & predictions logged into a forecast_logs table
- 📝 Stored fields: model, lag1/lag2/lag3, prediction, created_at
- 🔎 `/logs/latest` endpoint — fetch recent logs directly from API
- 🎛️ Frontend update — new “Show Logs” button to view recent predictions in a table
- 🔒 Keeps full history → ready for Power BI (v1.6) and cloud deploy (v1.7)

---

## 🖼️ Screenshots (v1.5)

- Frontend UI with forecast + logs

- API Swagger UI showing `/logs/latest`

---

## Quickstart (v1.5)

### 1. Train & save models (v1.2)
```powershell
# RandomForest
python src/eda_v1.2.py --input data/Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2"

# XGBoost
python src/eda_v1.2.py --input data/Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2 (XGB)" --model xgb
```

### 2. Setup PostgreSQL (v1.5)
```bash
-- Create database
CREATE DATABASE salesdb;

-- Run init_db() once to create tables
python -c "from src.db import init_db; init_db()"
```


### 3. Start FastAPI backend (with DB logging)
```bash
uvicorn src.api_v1_5:app --reload --port 8000
```

Endpoints:

· `/predict` → forecast + log result

· `/logs/latest` → fetch recent N logs

· `/docs` → Swagger auto-docs

### 4. Start Next.js frontend (v1.4+v1.5)
```bash
cd frontend
npm install
npm run dev
```
Runs at: http://localhost:3000

Make sure `.env.local` contains:
```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```
---

## Roadmap (iteration plan)

- [x] **1.0 — MVP**: Normalise CSV → KPIs → Monthly & Category charts → HTML report
- [x] **1.1 — Enhanced EDA**: Winsorisation, weekly/monthly aggregation, Top‑N, geo, profit contribution
- [x] **1.2 — Forecasting**: Monthly aggregate → RF/XGBoost → *Actual vs Forecast* chart → save model
- [x] **1.3 — FastAPI**: `/predict` endpoint returning JSON forecasts
- [x] **1.4 — Next.js**: horizon input → call API → render charts
- [x] **1.5 — PostgreSQL**: store forecasts & request logs
- [ ] **1.6 — Power BI**: direct PG connection for KPI dashboards
- [ ] **1.7 — Cloud deployment**: Azure (API + DB, EU region), Vercel/Azure SWA (frontend)
- [ ] **Final**: screenshots, architecture diagram, CI/CD, online demo

---

## Architecture (current → target)

**Now (v1.5)**
CSV → Forecast (RF/XGB) → Model.pkl → FastAPI API → Next.js frontend → **PostgreSQL logs**

**Target**  
```text
CSV / DWH ──> EDA (1.0/1.1) ──> Forecast (1.2) ──> FastAPI (1.3)
                                   │                   │
                                   ▼                   ▼
                              PostgreSQL (1.5) ──> Power BI (1.6)
                                   ▲
                                   │
                              Next.js (1.4)

Infra: Azure App Service/Container Apps + Azure Database for PostgreSQL + Vercel/Azure SWA (1.7)
```

---

## Project highlights

- End-to-end pipeline: from raw CSV → EDA → forecasting → API → frontend → DB logging
- Supports both RandomForest (baseline) and XGBoost, with reloadable saved models
- FastAPI backend now logs every forecast to PostgreSQL
- Next.js frontend extended with logs table for transparency
- Ready for BI dashboards (Power BI v1.6) and enterprise-style cloud deployment (Azure v1.7)

---

## 📂 Project structure

```text
.
├─ .github/
│  └─ workflows/
│     └─ smoke.yml      # Minimal CI (import + dependency check)
├─ assets/              # Screenshots used in README (KPI, Weekly, Forecast, etc.)
├─ data/                # Input data (Superstore.csv - not committed to Git)
├─ frontend/            # v1.4 Next.js frontend app
│  ├─ app/
│  │  └─ page.tsx       # Main UI (inputs + forecast + logs)
│  ├─ package.json
│  └─ .env.local (gitignored)
├─ reports/             # Generated reports, figures, models (gitignored)
│  ├─ figures/          # All PNG charts
│  └─ models/           # Saved ML models (.pkl)
├─ scripts/
│  ├─ run_eda.sh        # macOS/Linux helper
│  ├─ run_eda.ps1       # Windows PowerShell helper
├─ src/
│  ├─ eda_v1.0.py       # v1.0 script (MVP)
│  ├─ eda_v1.1.py       # v1.1 script (Enhanced EDA)
│  └─ eda_v1.2.py       # v1.2 script (Forecasting with RF/XGB)
│  └─ api_v1_3.py       # v1.3 FastAPI backend
│  ├─ api_v1_5.py         # v1.5 FastAPI backend (DB logging)
│  └─ db.py               # SQLAlchemy models + Session
├─ requirements.txt       # Python dependencies (now includes psycopg2, sqlalchemy, python-dotenv)
├─ LICENSE              # MIT License
└─ README.md            # Project documentation


```

---

## Dataset & licence

- Dataset: Kaggle *Sample Superstore* (public demo dataset)
- Intended for learning & portfolio use; not production
- Licence: MIT
