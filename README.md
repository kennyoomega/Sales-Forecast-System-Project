# Sales Forecast Intelligence (MVP 1.0)

**Goal:** A simple, EU-market-aligned data app skeleton. Today’s MVP runs an **EDA pipeline** on a sales CSV and produces a clean report (figures + summary).  
Next iterations will turn this into a **Full-Stack DS app** (FastAPI + Next.js + Postgres + Power BI).

## Folder structure
```
sales-forecast-mvp-1.0/
├─ data/                # sample_sales.csv (you can replace with your own CSV)
├─ notebooks/           # EDA notebook (for interview demo)
├─ src/                 # EDA pipeline scripts
├─ templates/           # HTML template for the report
├─ reports/             # auto-generated figures & report (gitignored)
├─ requirements.txt
└─ README.md
```

## Quickstart
1. Create & activate a virtual env:
   - Windows: `python -m venv venv && venv\Scripts\activate`
   - macOS/Linux: `python -m venv venv && source venv/bin/activate`
2. Install deps: `pip install -r requirements.txt`
3. Run EDA: `python src/eda.py --input data/sample_sales.csv --outdir reports`
4. Open the report: `reports/eda_report.html`
