# 🚀 Sales Forecast System (v1.7 — Cloud Deployment & Azure-Compatible)

A full-stack retail analytics and forecasting platform built on **FastAPI**, **PostgreSQL**, and **Next.js**, fully containerized with **Docker** and deployed across **Render**, **Vercel**, and **Neon Cloud** .
The system delivers end-to-end analytics from data ingestion to machine learning forecasts, cloud APIs, and interactive Power BI dashboards.

New in v1.7: completed **cloud deployment and Docker integration** — backend (FastAPI) on **Render**, frontend (Next.js) on **Vercel**, database on **Neon PostgreSQL Cloud**.
The entire stack is **fully portable to Azure App Service + Container Registry + Azure Database for PostgreSQL**, sharing the same Docker-based architecture.

Scope: Python EDA → forecasting → API → frontend → database logging → BI dashboards → **Dockerized cloud deployment (Azure-compatible)**.

---

## ✨ What’s new in v1.7

### Compared with v1.6 (Power BI), this version adds full deployment and containerization

- 🐳 **Dockerized architecture** — backend, database, and frontend orchestrated via `docker-compose` for consistent local & production setups
- ☁️ **Full cloud stack** — deployed via **Render** (API), **Vercel** (frontend), and **Neon** (PostgreSQL Cloud)
- 🔐 **CORS & environment variables** — unified `.env` configuration for cross-origin stability and secure secrets management
- 🌍 **Public demo** — live API endpoints connected to a responsive Next.js frontend
- ⚙️ **Azure-compatible design** — fully portable to **Azure App Service + Azure Container Registry + Azure PostgreSQL** with identical Docker images and CI/CD workflow
---

## ⚙️ Quickstart (v1.7)

### 1️⃣ Local Development (Dockerized)
```bash

# Build and start all containers
docker-compose up --build

```

API → http://localhost:8000

Frontend → http://localhost:3000

PostgreSQL → containerized instance with persistent volume

### 2️⃣ Cloud Deployment

| Service              | Platform                 | Command / Config                                           |
| -------------------- | ------------------------ | ---------------------------------------------------------- |
| **API**              | Render                   | `uvicorn src.api_v1_5:app --host 0.0.0.0 --port $PORT`     |
| **Frontend**         | Vercel                   | `npm run build && npm start`                               |
| **Database**         | Neon                     | Cloud PostgreSQL URL in `DATABASE_URL`                     |
| **Environment vars** | `.env` / Render / Vercel | `DATABASE_URL`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL` |


---


## 🖥️ Live Demo (v1.7)

| Layer                     | Platform                                                     | URL                              |
| :------------------------ | :----------------------------------------------------------- | :------------------------------- |
| **Frontend (Next.js)**    | [Vercel](https://sales-forecast-system-project.vercel.app)   | ✅ Live UI                        |
| **Backend (FastAPI)**     | [Render](https://sales-forecast-system-project.onrender.com) | ✅ Public API                     |
| **Database (PostgreSQL)** | [Neon Cloud](https://neon.tech)                              | Persistent data layer            |


---

## 🧩 Tech Stack

| Category                | Technology                   | Description                           |
| ----------------------- | ---------------------------- | ------------------------------------- |
| **Frontend**            | Next.js (React + TypeScript) | Forecast UI + logs table              |
| **Backend**             | FastAPI + SQLAlchemy         | API endpoints + DB logging            |
| **Database**            | Neon PostgreSQL              | Cloud-hosted managed PostgreSQL       |
| **ML Models**           | RandomForest / XGBoost       | Trained forecasting models (v1.2)     |
| **Visualization**       | Power BI                     | KPI dashboards and insights           |
| **Containerization**    | Docker + Docker Compose      | Unified local & cloud environment     |
| **Deployment**          | Render + Vercel              | Cost-efficient public hosting         |
| **Cloud compatibility** | Azure App Service + ACR      | Fully portable enterprise-grade setup |


---

## Roadmap (iteration plan)

- [x] **1.0 — MVP**: Normalise CSV → KPIs → Monthly & Category charts → HTML report
- [x] **1.1 — Enhanced EDA**: Winsorisation, weekly/monthly aggregation, Top‑N, geo, profit contribution
- [x] **1.2 — Forecasting**: Monthly aggregate → RF/XGBoost → *Actual vs Forecast* chart → save model
- [x] **1.3 — FastAPI**: `/predict` endpoint returning JSON forecasts
- [x] **1.4 — Next.js**: horizon input → call API → render charts
- [x] **1.5 — PostgreSQL**: store forecasts & request logs
- [x] **1.6 — Power BI**: direct PG connection for KPI dashboards
- [x] **1.7 — Docker + Cloud deployment**: Dockerised FastAPI + PostgreSQL + Next.js (Compose); pushed images to Render, Vercel, Neon (Azure-compatible)
- [ ] **Enhancement**: CI/CD pipelines, Power BI cloud refresh, Grafana integration
---

## 🏗️ Architecture Overview

**Current Deployment (v1.7)**
CSV → Forecast (RF/XGB) → Model.pkl → FastAPI API → Next.js frontend → PostgreSQL logs → Power BI dashboards → Docker + Render/Vercel (v1.7)

**Alternative (Enterprise)**  
```text
CSV / DWH ──> EDA (1.0/1.1) ──> Forecast (1.2) ──> FastAPI (1.3)
                                   │                   │
                                   ▼                   ▼
                              PostgreSQL (1.5) ──> Power BI (1.6)
                                   ▲
                                   │
                              Next.js (1.4)

Docker + Render + Vercel + Neon (v1.7) ──> Azure App Service + Container Registry (compatible)
```

---

## 🧾 Features

- 🔮 **ML forecasting** — RandomForest & XGBoost trained on Kaggle Superstore dataset

- ⚙️ **PI endpoints** — /predict, /models, /logs/latest (FastAPI)

- 🧱 **Persistent storage** — all predictions logged to Neon PostgreSQL

- 📈 **Analytics layer** — Power BI dashboards for KPIs, model mix & trends

- 🐳 **Docker support** — unified local dev & production setup

- ☁️ **Multi-cloud ready** — deployed via Render/Vercel, portable to Azure

- 🔐 **CORS-secured architecture** — verified full-stack communication chain

---

## 📂 Project structure

```text
.
├─ .github/
│  └─ workflows/
│     └─ smoke.yml      # Minimal CI (import + dependency check)
├─ assets/              # Screenshots (Overview, Model Ratio, Logs Table)
├─ backend/
│  ├─ Dockerfile
├─ data/                # Input data (Superstore.csv - not committed to Git)
├─ frontend/            # v1.4 Next.js frontend app
│  ├─ app/
│  │  └─ page.tsx       # Main UI (inputs + forecast + logs)
│  ├─ package.json
│  ├─ .env.local (gitignored)
│  └─ Dockerfile
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
│  ├─ api_v1_5.py       # v1.5 FastAPI backend (DB logging)
│  └─ db.py             # SQLAlchemy models + Session
├─ requirements.txt     # Python dependencies (now includes psycopg2, sqlalchemy, python-dotenv)
├─ docker-compose.yml    # Multi-service orchestration
├─ LICENSE              # MIT License
└─ README.md            # Project documentation


```

---

## Dataset & licence

- Dataset: Kaggle *Sample Superstore* (public demo dataset)
- Intended for learning & portfolio use; not production
- Licence: MIT

---

### 💬 Built with ❤️ using FastAPI, Next.js, PostgreSQL, Docker, and Power BI — bridging data science, engineering, and cloud architecture.
