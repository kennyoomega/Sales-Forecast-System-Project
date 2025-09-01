"""
Retail EDA v1.1
Adds: winsorisation, weekly trend, Top-N sub-categories, price vs qty scatter (with sampling),
profit contribution & margin, geo Top-N, HTML report with run flags.
"""

import argparse, textwrap, json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# --------------------------- utils ---------------------------

def ensure_outdirs(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    figs = outdir / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    return figs

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().replace("\n", " ").replace("\r", " ") for c in df.columns]

    # Order Date
    # allow: Order Date / order date / order_date / orderdate
    lower = {c.lower(): c for c in df.columns}
    for key in ["order date", "order_date", "orderdate"]:
        if key in lower:
            df.rename(columns={lower[key]: "Order Date"} , inplace=True)
            break
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

    # Simple renames for required columns
    for want in ["Sales", "Quantity", "Profit", "Category", "Sub-Category"]:
        if want not in df.columns:
            for c in df.columns:
                if c.lower().replace("-", "").replace(" ", "") == want.lower().replace("-", "").replace(" ", ""):
                    df.rename(columns={c: want}, inplace=True)

    # Geo
    for want in ["Region", "State", "City"]:
        if want not in df.columns:
            for c in df.columns:
                if c.lower() == want.lower():
                    df.rename(columns={c: want}, inplace=True)
    return df

def winsorize_columns(df: pd.DataFrame, cols, pct: float) -> pd.DataFrame:
    if pct <= 0: 
        return df
    df = df.copy()
    for c in cols:
        if c in df.columns:
            lo, hi = df[c].quantile(pct), df[c].quantile(1 - pct)
            df[c] = df[c].clip(lo, hi)
    return df

def kpis(df: pd.DataFrame) -> dict:
    order_id_col = next((c for c in df.columns if c.lower() in ["order id","order_id","orderid"]), None)
    total_sales  = float(df["Sales"].sum()) if "Sales" in df.columns else float("nan")
    total_orders = int(df[order_id_col].nunique()) if order_id_col else int(df.shape[0])
    if order_id_col and "Sales" in df.columns:
        order_sales = df.groupby(order_id_col)["Sales"].sum()
        aov = float(order_sales.mean())
    else:
        aov = float(df["Sales"].mean()) if "Sales" in df.columns else float("nan")
    return {"total_sales": total_sales, "total_orders": total_orders, "aov": aov}


# --------------------------- plots ---------------------------

def plot_monthly_revenue(df, figs_dir, dpi=120):
    if "Order Date" not in df.columns or "Sales" not in df.columns: return ""
    ts = df.dropna(subset=["Order Date"]).set_index("Order Date")["Sales"].resample("MS").sum()
    plt.figure(figsize=(10,4), dpi=dpi); ts.plot(marker="o")
    plt.title("Monthly Revenue"); plt.ylabel("Sales"); plt.xlabel("Month"); plt.tight_layout()
    path = figs_dir/"monthly_revenue.png"; plt.savefig(path); plt.close(); return str(path)

def plot_weekly_revenue(df, figs_dir, dpi=120):
    if "Order Date" not in df.columns or "Sales" not in df.columns: return ""
    ts = df.dropna(subset=["Order Date"]).set_index("Order Date")["Sales"].resample("W-SUN").sum()
    plt.figure(figsize=(10,4), dpi=dpi); ts.plot()
    plt.title("Weekly Revenue (Sun-ended)"); plt.ylabel("Sales"); plt.xlabel("Week"); plt.tight_layout()
    path = figs_dir/"weekly_revenue.png"; plt.savefig(path); plt.close(); return str(path)

def plot_category_revenue(df, figs_dir, dpi=120):
    if "Category" not in df.columns or "Sales" not in df.columns: return ""
    ser = df.groupby("Category")["Sales"].sum().sort_values(ascending=False)
    plt.figure(figsize=(8,4), dpi=dpi); ser.plot(kind="bar")
    plt.title("Revenue by Category"); plt.ylabel("Sales"); plt.xlabel("Category"); plt.tight_layout()
    path = figs_dir/"category_revenue.png"; plt.savefig(path); plt.close(); return str(path)

def plot_top_subcategories(df, figs_dir, top_n=10, dpi=120):
    if "Sub-Category" not in df.columns or "Sales" not in df.columns: return ""
    ser = df.groupby("Sub-Category")["Sales"].sum().sort_values(ascending=False).head(top_n)
    plt.figure(figsize=(10,5), dpi=dpi); ser.iloc[::-1].plot(kind="barh")
    plt.title(f"Top {top_n} Sub-Categories by Revenue"); plt.xlabel("Sales"); plt.ylabel("Sub-Category"); plt.tight_layout()
    path = figs_dir/"top_subcategories.png"; plt.savefig(path); plt.close(); return str(path)

def plot_price_vs_qty(df, figs_dir, sample_n=2000, dpi=120):
    if "Sales" not in df.columns or "Quantity" not in df.columns: return ""
    sdf = df[(df["Quantity"] > 0) & (df["Sales"] >= 0)].copy()
    if sdf.empty: return ""
    sdf["UnitPrice"] = sdf["Sales"]/sdf["Quantity"]
    if sdf.shape[0] > sample_n:
        sdf = sdf.sample(sample_n, random_state=42)
    plt.figure(figsize=(6,5), dpi=dpi); plt.scatter(sdf["UnitPrice"], sdf["Quantity"], alpha=0.4)
    plt.title("Unit Price vs Quantity (sampled)"); plt.xlabel("Unit Price"); plt.ylabel("Quantity"); plt.tight_layout()
    path = figs_dir/"price_vs_quantity.png"; plt.savefig(path); plt.close(); return str(path)

def plot_profit_contribution(df, figs_dir, dpi=120):
    if "Profit" not in df.columns or "Sales" not in df.columns or "Category" not in df.columns: return "", ""
    cat = df.groupby("Category")[["Sales","Profit"]].sum().sort_values("Profit", ascending=False)
    # Profit contribution
    plt.figure(figsize=(8,4), dpi=dpi); cat["Profit"].plot(kind="bar")
    plt.title("Profit Contribution by Category"); plt.ylabel("Profit"); plt.tight_layout()
    p1 = figs_dir/"profit_contribution_by_category.png"; plt.savefig(p1); plt.close()
    # Profit margin
    margin = (cat["Profit"]/cat["Sales"]).replace([np.inf,-np.inf],np.nan)
    plt.figure(figsize=(8,4), dpi=dpi); margin.plot(kind="bar")
    plt.title("Profit Margin by Category"); plt.ylabel("Profit / Sales"); plt.tight_layout()
    p2 = figs_dir/"profit_margin_by_category.png"; plt.savefig(p2); plt.close()
    return str(p1), str(p2)

def plot_geo_top(df, figs_dir, top_n=10, dpi=120):
    geo_col = next((c for c in ["State","Region","City"] if c in df.columns), None)
    if not geo_col or "Sales" not in df.columns: return ""
    ser = df.groupby(geo_col)["Sales"].sum().sort_values(ascending=False).head(top_n)
    plt.figure(figsize=(10,5), dpi=dpi); ser.iloc[::-1].plot(kind="barh")
    plt.title(f"Top {top_n} {geo_col}s by Revenue"); plt.xlabel("Sales"); plt.ylabel(geo_col); plt.tight_layout()
    path = figs_dir/f"top_{geo_col.lower()}s_by_revenue.png"; plt.savefig(path); plt.close(); return str(path)


# --------------------------- report ---------------------------

def write_html_report(outdir: Path, title: str, kpi: dict, fig_paths: list[str], flags: dict):
    html = outdir / "eda_report_1_1.html"
    
    figs_html = "\n".join([
    f'<div class="fig"><img src="figures/{Path(p).name}" /></div>'
    for p in fig_paths if p
])

    kpi_html = f"""
    <div class="kpis">
      <div class="kpi"><span>Total Sales</span><strong>{kpi.get('total_sales', float('nan')):,.2f}</strong></div>
      <div class="kpi"><span>Total Orders</span><strong>{kpi.get('total_orders', 0):,}</strong></div>
      <div class="kpi"><span>Average Order Value</span><strong>{kpi.get('aov', float('nan')):,.2f}</strong></div>
    </div>
    """
    css = """
    <style>
      body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
      h1 { margin-bottom: 8px; }
      .meta { color:#666; margin-bottom: 16px; }
      .kpis { display:flex; gap:16px; margin: 16px 0 24px; }
      .kpi {flex:1;display:flex;justify-content:space-between;align-items:center;
      padding:16px;border:1px solid #eee;border-radius:12px;background:#fafafa;
      box-shadow:0 1px 4px rgba(0,0,0,0.08);}
      .kpi span{font-size:14px;color:#666;margin-right:8px;}
      .kpi strong{font-size:20px;font-weight:600;}
      .fig { margin: 18px 0; }
      img { max-width: 100%; height:auto; border: 1px solid #eee; border-radius: 8px; }
      pre { background:#f6f8fa; padding:12px; border-radius:8px; overflow:auto; }
    </style>
    """
    with html.open("w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body>")
        f.write(f"<h1>{title}</h1>")
        f.write(f"<div class='meta'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>")
        f.write("<h2>KPIs</h2>")
        f.write(kpi_html)
        f.write("<h2>Figures</h2>")
        f.write(figs_html)
        f.write("<h2>Run Config</h2>")
        f.write(f"<pre>{json.dumps(flags, indent=2)}</pre>")
        f.write("</body></html>")
    return str(html)


# --------------------------- main ---------------------------

def main():
    p = argparse.ArgumentParser(description="Retail EDA v1.1 (Superstore-ready)")
    p.add_argument("--input", required=True, help="Path to Superstore.csv")
    p.add_argument("--outdir", default="reports", help="Output directory")
    p.add_argument("--title", default="Retail EDA — MVP 1.1")
    p.add_argument("--dpi", type=int, default=120)

    # 1.1 feature flags
    p.add_argument("--winsor-pct", type=float, default=0.0, help="Clip Sales/Profit by pct tails, e.g. 0.01")
    p.add_argument("--enable-weekly", type=int, default=0, help="Weekly revenue chart")
    p.add_argument("--enable-subcat", type=int, default=0, help="Top-N sub-categories by revenue")
    p.add_argument("--enable-priceqty", type=int, default=0, help="Unit price vs quantity scatter (sampled)")
    p.add_argument("--enable-profit", type=int, default=0, help="Profit contribution & margin charts")
    p.add_argument("--enable-geo", type=int, default=0, help="Top regions/states/cities by revenue")
    p.add_argument("--top-n", type=int, default=10, help="Top-N for sub-cats and geo charts")
    p.add_argument("--sample-n", type=int, default=2000, help="Sample size for scatter chart")

    args = p.parse_args()

    in_path = Path(args.input)
    outdir = Path(args.outdir)
    figs_dir = ensure_outdirs(outdir)

    # Load & normalise
    try:
        df = pd.read_csv(in_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(in_path, encoding="latin1", low_memory=False)

    df = normalise_columns(df)
    if "Order Date" in df.columns:
        df = df[~df["Order Date"].isna()].copy()

    # Winsorization
    df_clean = winsorize_columns(df, ["Sales", "Profit"], args.winsor_pct)

    # KPIs
    kpi_vals = kpis(df_clean)

    # Always: monthly + category
    figs = []
    figs.append(plot_monthly_revenue(df_clean, figs_dir, dpi=args.dpi))
    figs.append(plot_category_revenue(df_clean, figs_dir, dpi=args.dpi))

    # Optional features
    if args.enable_weekly:
        figs.append(plot_weekly_revenue(df_clean, figs_dir, dpi=args.dpi))
    if args.enable_subcat:
        figs.append(plot_top_subcategories(df_clean, figs_dir, top_n=args.top_n, dpi=args.dpi))
    if args.enable_priceqty:
        figs.append(plot_price_vs_qty(df_clean, figs_dir, sample_n=args.sample_n, dpi=args.dpi))
    if args.enable_profit:
        p1, p2 = plot_profit_contribution(df_clean, figs_dir, dpi=args.dpi)
        figs.extend([p1, p2])
    if args.enable_geo:
        figs.append(plot_geo_top(df_clean, figs_dir, top_n=args.top_n, dpi=args.dpi))

    # Record flags for reproducibility
    flags = {
        "winsor_pct": args.winsor_pct,
        "enable_weekly": bool(args.enable_weekly),
        "enable_subcat": bool(args.enable_subcat),
        "enable_priceqty": bool(args.enable_priceqty),
        "enable_profit": bool(args.enable_profit),
        "enable_geo": bool(args.enable_geo),
        "top_n": args.top_n,
        "sample_n": args.sample_n,
        "dpi": args.dpi,
    }

    report_path = write_html_report(outdir, args.title, kpi_vals, figs, flags)
    print(f"[OK] Report written to: {report_path}")
    print(f"[OK] Figures in: {figs_dir.resolve()}")

if __name__ == "__main__":
    main()
