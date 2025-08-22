# 🛒 Sales Forecast System

A real-data, full-stack retail analytics foundation using the Kaggle Superstore dataset.
Demonstrates business-oriented EDA, a roadmap to ML forecasting, and extension into APIs, frontend, databases, BI dashboards, and cloud deployment – aligned with the tech stack widely used in EU companies.

---

## ✨ What’s in v1.0 (MVP)
- ✅ **Schema normalisation** for Superstore fields (`Order Date`, `Sales`, `Quantity`, `Category`, …)  
- ✅ **KPIs**: Total Revenue, Total Orders, Average Order Value (order-level where possible)  
- ✅ **Charts**:  
  - 📈 Monthly revenue trend  
  - 📊 Revenue by category  
- ✅ **Deliverable**: Lightweight, responsive **HTML report** (`reports/eda_report.html`)  
- ✅ **Feature flags pre-wired** (default OFF) so 1.1+ unlock without refactor

---

## 🚀 Quickstart

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python src\eda_v1.0.py --input data\Superstore.csv --outdir reports --title "Retail EDA — MVP 1.0"

macOS / Linux
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python src/eda_v1.0.py --input data/Superstore.csv --outdir reports --title "Retail EDA — MVP 1.0"

👉 Open reports/eda_report.html in your browser.

🔓 Unlock 1.1 Features (optional flags)
Already implemented, but OFF by default. Toggle them like this:

python src/eda_v1.0.py --input data/Superstore.csv --outdir reports \
  --enable-subcat 1 --enable-priceqty 1 --enable-profit 1 \
  --enable-geo 1 --enable-weekly 1 --winsor-pct 0.01
Flags

--enable-subcat → Top-N sub-categories by revenue

--enable-priceqty → Price vs Quantity scatter (sampled)

--enable-profit → Profit margin / contribution charts

--enable-geo → Top regions (auto-selects State/City/Region)

--enable-weekly → Weekly revenue trend

--winsor-pct → Outlier clipping (e.g. 0.01 trims 1% tails)

📊 Roadmap (Iteration Plan)
 1.0 — MVP: Normalise CSV → KPIs → Monthly & Category charts → HTML report

 1.1 — Enhanced EDA: Winsorisation, weekly/monthly, Top-N, geo, profit contribution

 1.2 — Forecasting: Aggregate monthly → RF/XGBoost → Actual vs Forecast chart → save model

 1.3 — FastAPI: /predict endpoint returning JSON forecasts

 1.4 — Next.js: Horizon input → call API → render charts

 1.5 — PostgreSQL: Store forecasts & request logs

 1.6 — Power BI: Direct PG connection for KPI dashboards

 1.7 — Cloud Deployment: Azure (API+DB, EU region), Vercel/Azure SWA (Frontend)

 Final Deliverable: Screenshots, architecture diagram, CI/CD, online demo

📐 Architecture (current → target)
Now (1.0):
CSV → Normalise → KPIs + Charts → HTML report

Target:
CSV / DWH ──> EDA (1.0/1.1) ──> Forecast (1.2) ──> FastAPI (1.3)
                                   │                   │
                                   ▼                   ▼
                              PostgreSQL (1.5) ──> Power BI (1.6)
                                   ▲
                                   │
                              Next.js (1.4)

Infra: Azure App Service/Container Apps + Azure Database for PostgreSQL + Vercel/Azure SWA (1.7)
📌 Why this matters (for EU retail/data teams)
Business value: Fast revenue trends, category mix, profitability signals.

Explainability first: Simple KPIs/charts before ML so stakeholders trust results.

Operational path: Clear evolution into API + DB + BI on Azure/Power BI stack widely used in EU.

Privacy-aware: Runs locally, GDPR-conscious by design (no PII in reports).

📂 Project structure
.
├─ data/                # Superstore.csv (not committed)
├─ reports/             # Generated artefacts (gitignored)
├─ src/
│  └─ eda_v1.0.py       # Main app (flags included, default OFF)
├─ scripts/
│  ├─ run_eda.sh        # macOS/Linux helper
│  ├─ run_eda.ps1       # Windows PowerShell helper
│  └─ run_eda.bat       # Windows CMD helper
├─ requirements.txt
└─ README.md
