
import argparse, os, math
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ---------- Utils ----------
def ensure_dir(p): os.makedirs(p, exist_ok=True)

def fmt_currency(x):
    try: return f"${x:,.2f}"
    except: return "—"

# ---------- Load & Normalize (Superstore-ready) ----------
def load_data(path):
    # Robust read with encoding fallback
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1")
    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    # map common superstore names -> canonical schema
    rename = {}

    # date
    for cand in ["order date", "order_date", "orderdate", "date"]:
        if cand in df.columns: rename[cand] = "date"; break

    # revenue (sales)
    for cand in ["sales", "revenue", "amount"]:
        if cand in df.columns: rename[cand] = "revenue"; break

    # quantity
    for cand in ["quantity", "qty", "order quantity", "order_quantity"]:
        if cand in df.columns: rename[cand] = "quantity"; break

    # category
    for cand in ["category"]:
        if cand in df.columns: rename[cand] = "category"; break

    # sub-category
    for cand in ["sub-category", "sub_category"]:
        if cand in df.columns: rename[cand] = "sub_category"; break

    # order id
    for cand in ["order id", "order_id", "orderid"]:
        if cand in df.columns: rename[cand] = "order_id"; break

    # profit
    for cand in ["profit"]:
        if cand in df.columns: rename[cand] = "profit"; break

    df = df.rename(columns=rename)

    # types
    if "date" not in df.columns:
        raise ValueError("No order date found (expect 'Order Date' or similar).")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for c in ["revenue", "quantity", "profit"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # derive price if possible
    if "price" not in df.columns:
        if "revenue" in df.columns and "quantity" in df.columns:
            q = df["quantity"].replace(0, np.nan)
            df["price"] = df["revenue"] / q
        else:
            df["price"] = np.nan

    # category fallback
    if "category" not in df.columns and "sub_category" in df.columns:
        df["category"] = df["sub_category"]

    # temporal helpers
    df = df.dropna(subset=["date", "revenue"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df

# ---------- KPIs ----------
def compute_kpis(df):
    total_rev = float(df["revenue"].sum())
    if "order_id" in df.columns:
        orders = df.groupby("order_id", as_index=False)["revenue"].sum()
        total_orders = int(len(orders))
        aov = float(orders["revenue"].mean()) if total_orders > 0 else float("nan")
    else:
        total_orders = int(df.shape[0])
        aov = float(df["revenue"].mean()) if total_orders > 0 else float("nan")
    return {"total_rev": total_rev, "total_orders": total_orders, "aov": aov}

# ---------- Plots (minimal 1.0) ----------
def plot_monthly(df, outdir):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "monthly_revenue.png")
    monthly = df.groupby("month", as_index=False)["revenue"].sum().sort_values("month")
    plt.figure(figsize=(9,4.5))
    plt.plot(monthly["month"], monthly["revenue"], marker="o")
    plt.title("Monthly Revenue")
    plt.xlabel("Month")
    plt.ylabel("Revenue")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(p, dpi=180); plt.close()
    return p

def plot_category(df, outdir):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "category_revenue.png")
    if "category" in df.columns:
        cat = df.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
        plt.figure(figsize=(9,4.5))
        plt.bar(cat["category"], cat["revenue"])
        plt.title("Revenue by Category")
        plt.xlabel("Category")
        plt.ylabel("Revenue")
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        plt.savefig(p, dpi=180); plt.close()
    return p


def plot_subcategory_topn(df, outdir, n=10):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "subcategory_topn.png")
    if "sub_category" in df.columns:
        sub = df.groupby("sub_category", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False).head(n)
        if not sub.empty:
            plt.figure(figsize=(9,4.5))
            plt.bar(sub["sub_category"], sub["revenue"])
            plt.title(f"Top {n} Sub-Categories by Revenue")
            plt.xlabel("Sub-Category"); plt.ylabel("Revenue")
            plt.xticks(rotation=25, ha="right"); plt.tight_layout()
            plt.savefig(p, dpi=180); plt.close()
    return p


def plot_price_qty(df, outdir):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "price_vs_quantity.png")
    if "price" in df.columns and "quantity" in df.columns:
        sample = df.dropna(subset=["price", "quantity"])
        if len(sample) > 5000:
            sample = sample.sample(5000, random_state=42)
        if not sample.empty:
            plt.figure(figsize=(6.5,6))
            plt.scatter(sample["quantity"], sample["price"], s=10, alpha=0.5)
            plt.title("Unit Price vs Quantity (sampled)")
            plt.xlabel("Quantity"); plt.ylabel("Unit Price")
            plt.tight_layout(); plt.savefig(p, dpi=180); plt.close()
    return p


def plot_profit_margin(df, outdir):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "profit_margin_by_category.png")
    if "profit" in df.columns and "category" in df.columns:
        agg = df.groupby("category", as_index=False).agg(revenue=("revenue","sum"), profit=("profit","sum"))
        if not agg.empty:
            agg["margin"] = agg["profit"] / agg["revenue"]
            agg = agg.sort_values("margin", ascending=False)
            plt.figure(figsize=(9,4.5))
            plt.bar(agg["category"], agg["margin"])
            plt.title("Profit Margin by Category")
            plt.xlabel("Category"); plt.ylabel("Margin")
            plt.xticks(rotation=25, ha="right"); plt.tight_layout()
            plt.savefig(p, dpi=180); plt.close()
    return p


def best_geo_level(df):
    for col in ["state", "city", "region"]:
        if col in df.columns: return col
    return None

def plot_geo_topn(df, outdir, n=15):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "geo_topn_revenue.png")
    lvl = best_geo_level(df)
    if lvl is None: return p
    grp = df.groupby(lvl, as_index=False)["revenue"].sum().sort_values("revenue", ascending=False).head(n)
    if not grp.empty:
        plt.figure(figsize=(10,5))
        plt.bar(grp[lvl].astype(str), grp["revenue"])
        plt.title(f"Top {n} {lvl.title()} by Revenue")
        plt.xlabel(lvl.title()); plt.ylabel("Revenue")
        plt.xticks(rotation=25, ha="right"); plt.tight_layout()
        plt.savefig(p, dpi=180); plt.close()
    return p


def plot_weekly(df, outdir):
    ensure_dir(os.path.join(outdir, "figures"))
    p = os.path.join(outdir, "figures", "weekly_revenue.png")
    if "date" in df.columns:
        tmp = df.copy()
        tmp["week"] = tmp["date"].dt.to_period("W").dt.to_timestamp()
        weekly = tmp.groupby("week", as_index=False)["revenue"].sum().sort_values("week")
        if not weekly.empty:
            plt.figure(figsize=(9,4.5))
            plt.plot(weekly["week"], weekly["revenue"], marker="o")
            plt.title("Weekly Revenue")
            plt.xlabel("Week"); plt.ylabel("Revenue")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout(); plt.savefig(p, dpi=180); plt.close()
    return p


def winsorize(series, pct=0.01):
    if pct <= 0 or pct >= 0.5 or series.isna().all():
        return series
    lo = series.quantile(pct)
    hi = series.quantile(1-pct)
    return series.clip(lower=lo, upper=hi)

# ---------- HTML (self-contained, no Jinja) ----------
def render_html(kpis, outdir, title="Superstore EDA — MVP 1.0", figs=None, source_name=None):
    if figs is None: figs = []
    style = """
    <style>
      body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #1f2937; }
      h1 { font-size: 26px; margin-bottom: 6px; }
      .muted { color: #6b7280; }
      .kpis { display: grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 12px; margin:14px 0 22px; }
      .card { border:1px solid #e5e7eb; border-radius:12px; padding:12px; box-shadow:0 1px 2px rgba(0,0,0,0.04); }
      .label { font-size:12px; color:#6b7280; }
      .value { font-size:20px; font-weight:600; margin-top:6px; }
      .grid { display:grid; grid-template-columns: repeat(2,1fr); gap: 14px; }
      img { width:100%; border:1px solid #e5e7eb; border-radius:12px; padding:6px; background:#fff; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } .kpis { grid-template-columns: 1fr; } }
    </style>
    """
    def v(x, cur=False):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))): return "—"
        return fmt_currency(x) if cur else f"{x:,.0f}"

    imgs = "".join([f"<div><img src='{os.path.relpath(p, outdir)}' alt='chart'></div>" 
                    for p in figs if p and os.path.exists(p)])

    html = f"""
    <!doctype html><html><head><meta charset='utf-8'><title>{title}</title>{style}</head>
    <body>
      <h1>{title}</h1>
      <div class='muted'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
      <div class='kpis'>
        <div class='card'><div class='label'>Total Revenue</div><div class='value'>{v(kpis.get('total_rev'), cur=True)}</div></div>
        <div class='card'><div class='label'>Total Orders</div><div class='value'>{v(kpis.get('total_orders'))}</div></div>
        <div class='card'><div class='label'>Average Order Value</div><div class='value'>{v(kpis.get('aov'), cur=True)}</div></div>
      </div>
      <h2>Trends</h2>
      <div class='grid'>{imgs}</div>
      <div class='muted' style='margin-top:16px'>Data source: {source_name or "CSV"}</div>
      <div class='muted'>MVP 1.0 — EDA first; ML, API, FE, DB in upcoming versions.</div>
    </body></html>
    """
    out = os.path.join(outdir, "eda_report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out

# ---------- Main ----------
def run(input_csv, outdir, title="Superstore EDA — MVP 1.0", enable_subcat=0, enable_priceqty=0, enable_profit=0, enable_geo=0, enable_weekly=0, winsor_pct=0.0):
    ensure_dir(outdir); ensure_dir(os.path.join(outdir, "figures"))
    df = load_data(input_csv)
    # optional light cleaning (winsor)
    if winsor_pct and winsor_pct > 0:
        if 'revenue' in df.columns: df['revenue'] = winsorize(df['revenue'], pct=winsor_pct)
        if 'price' in df.columns: df['price'] = winsorize(df['price'], pct=winsor_pct)
    k = compute_kpis(df)
    figs = []
    f1 = plot_monthly(df, outdir); figs.append(f1)
    f2 = plot_category(df, outdir); figs.append(f2)
    if enable_weekly: figs.append(plot_weekly(df, outdir))
    if enable_subcat: figs.append(plot_subcategory_topn(df, outdir, n=10))
    if enable_priceqty: figs.append(plot_price_qty(df, outdir))
    if enable_profit:
        figs.append(plot_profit_margin(df, outdir))
    if enable_geo: figs.append(plot_geo_topn(df, outdir, n=15))
    html = render_html(k, outdir, title=title, figs=figs, source_name=os.path.basename(input_csv))
    return html

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to Superstore-like CSV")
    ap.add_argument("--outdir", default="reports", help="Where to save report/assets")
    ap.add_argument("--title", default="Superstore EDA — MVP 1.0")
    # feature flags (default OFF for 1.0)
    ap.add_argument("--enable-subcat", type=int, default=0)
    ap.add_argument("--enable-priceqty", type=int, default=0)
    ap.add_argument("--enable-profit", type=int, default=0)
    ap.add_argument("--enable-geo", type=int, default=0)
    ap.add_argument("--enable-weekly", type=int, default=0)
    ap.add_argument("--winsor-pct", type=float, default=0.0)
    args = ap.parse_args()
    out = run(args.input, args.outdir, title=args.title,
               enable_subcat=args.enable_subcat,
               enable_priceqty=args.enable_priceqty,
               enable_profit=args.enable_profit,
               enable_geo=args.enable_geo,
               enable_weekly=args.enable_weekly,
               winsor_pct=args.winsor_pct)
    print("Report generated:", out)

if __name__ == "__main__":
    main()
