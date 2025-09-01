# Sales Forecast System (v1.2 — Forecasting)

A full-stack retail analytics MVP built on Kaggle’s *Superstore* dataset.  

**New in v1.2:** first forecasting module. Monthly sales aggregated, lag features engineered, RandomForest / XGBoost trained, *Actual vs Forecast* chart generated, and model persisted for future API use.  

(Supports both RandomForest (baseline) and XGBoost (boosted trees).
The choice is controlled via --model {rf|xgb}, with artifacts saved separately under reports/models/.
Forecast results are visualized as Actual vs Forecast charts for quick comparison.)

Scope: Python EDA → forecasting → API → frontend → database logging → BI → Azure deployment.

⚡ Note: This project is built on a retail dataset (Superstore). However, the **pipeline design (SQL → ML forecasting → BI dashboards → Azure deployment)** is domain-agnostic and can be directly applied to **banking KPI monitoring, credit risk scoring, or industrial forecasting**.  


---

## ✨ What’s new in v1.2

Compared with **v1.1 (Enhanced EDA)**, this version adds **predictive capability**:

- ⏳ **Monthly aggregation** — sales resampled by month  
- 🔁 **Lag features** — past 3 months’ sales as predictors  
- 🌲 **RandomForest forecasting** — baseline model  
- ⚡ **XGBoost forecasting** — optional via `--model xgb`  
- 📊 **Actual vs Forecast chart** — visual side-by-side comparison  
- 💾 **Model persistence** — saved in `reports/models/` for FastAPI integration  

👉 This marks the transition from *descriptive analytics* → *predictive modeling*.

---

## 🖼️ Screenshots (v1.2)

**RandomForest (baseline)** 
![Forecast vs Actual(RF)](assets/forecast_vs_actual(RF).png)

**XGBoost (boosted trees)**
![Forecast vs Actual(XGBoost)](assets/forecast_vs_actual(XG).png)

---

## Quickstart (v1.2)

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run with RandomForest (default)
python src\eda_v1.2.py --input data\Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2"

# Run with XGBoost
python src\eda_v1.2.py --input data\Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2 (XGBoost)" --model xgb

# Run with longer test horizon (last 6 months)
python src\eda_v1.2.py --input data\Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2 (XGB, 6m test)" --model xgb --horizon 6


```

### macOS / Linux
```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run with RandomForest
python src/eda_v1.2.py --input data/Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2"

# Run with XGBoost
python src/eda_v1.2.py --input data/Superstore.csv --outdir reports --title "Retail EDA — MVP 1.2 (XGBoost)" --model xgb


```

Output: open reports/eda_report_1_2.html in your browser.
Model saved in: reports/models/.

---

## Roadmap (iteration plan)

- [x] **1.0 — MVP**: Normalise CSV → KPIs → Monthly & Category charts → HTML report
- [x] **1.1 — Enhanced EDA**: Winsorisation, weekly/monthly aggregation, Top‑N, geo, profit contribution
- [x] **1.2 — Forecasting**: Monthly aggregate → RF/XGBoost → *Actual vs Forecast* chart → save model
- [ ] **1.3 — FastAPI**: `/predict` endpoint returning JSON forecasts
- [ ] **1.4 — Next.js**: horizon input → call API → render charts
- [ ] **1.5 — PostgreSQL**: store forecasts & request logs
- [ ] **1.6 — Power BI**: direct PG connection for KPI dashboards
- [ ] **1.7 — Cloud deployment**: Azure (API + DB, EU region), Vercel/Azure SWA (frontend)
- [ ] **Final**: screenshots, architecture diagram, CI/CD, online demo

---

## Architecture (current → target)

**Now (1.2)**
CSV → Normalise → KPIs + Charts + Forecast (RF/XGB) → HTML report + Model.pkl

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

- Demonstrates evolution from descriptive → predictive analytics
- Supports both RandomForest and XGBoost
- Model persistence ensures compatibility with APIs/DBs
- Stakeholder-ready reports + ML outputs in one package

---

## 📂 Project structure

```text
.
├─ .github/
│  └─ workflows/
│     └─ smoke.yml      # Minimal CI (import + dependency check)
├─ assets/              # Screenshots used in README (KPI, Weekly, Forecast, etc.)
├─ data/                # Input data (Superstore.csv - not committed to Git)
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
├─ requirements.txt     # Python dependencies
├─ LICENSE              # MIT License
└─ README.md            # Project documentation


```

---

## Dataset & licence

- Dataset: Kaggle *Sample Superstore* (public demo dataset)
- Intended for learning & portfolio use; not production
- Licence: MIT
