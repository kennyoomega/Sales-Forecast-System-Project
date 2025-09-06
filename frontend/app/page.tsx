"use client";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
type ModelName = "rf" | "xgb";

export default function Home() {
  const [lag1, setLag1] = useState<number>(30000);
  const [lag2, setLag2] = useState<number>(28000);
  const [lag3, setLag3] = useState<number>(25000);
  const [model, setModel] = useState<ModelName>("rf");
  const [available, setAvailable] = useState<ModelName[]>(["rf"]);
  const [yhat, setYhat] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  // 拉取后端可用模型列表（rf / xgb）
  useEffect(() => {
    fetch(`${API_BASE}/models`).then(r => r.json()).then(d => {
      if (Array.isArray(d.available_models) && d.available_models.length) {
        setAvailable(d.available_models);
        // 默认选第一个可用的
        setModel(d.available_models.includes("rf") ? "rf" : (d.available_models[0] as ModelName));
      }
    }).catch(() => {});
  }, []);

  const onPredict = async () => {
    try {
      setLoading(true);
      setErr("");
      const url = `${API_BASE}/predict?lag1=${lag1}&lag2=${lag2}&lag3=${lag3}&model=${model}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
      const data = await resp.json();
      setYhat(data.prediction);
    } catch (e: any) {
      setErr(e.message || "Request failed");
      setYhat(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial" }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>Sales Forecast — v1.4 (Frontend)</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>Calls FastAPI v1.3 with selectable model.</p>

      {/* 选择模型 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: "#555", marginBottom: 6 }}>Model</div>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value as ModelName)}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
        >
          {available.map(m => (
            <option key={m} value={m}>
              {m === "rf" ? "RandomForest (rf)" : "XGBoost (xgb)"}
            </option>
          ))}
        </select>
      </div>

      {/* 三个 lag 输入 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <Field label="lag1 (last month)" value={lag1} onChange={v => setLag1(v)} />
        <Field label="lag2 (2 months ago)" value={lag2} onChange={v => setLag2(v)} />
        <Field label="lag3 (3 months ago)" value={lag3} onChange={v => setLag3(v)} />
      </div>

      <button onClick={onPredict}
        disabled={loading}
        style={{ marginTop: 16, padding: "10px 16px", borderRadius: 10, border: "1px solid #222",
                 background: loading ? "#777" : "#111", color: "#fff", cursor: loading ? "not-allowed" : "pointer" }}>
        {loading ? "Predicting..." : `Predict with ${model.toUpperCase()}`}
      </button>

      {err && <div style={{ marginTop: 12, color: "#b00020" }}>Error: {err}</div>}

      {yhat !== null && !err && (
        <div style={{ marginTop: 20, padding: 16, border: "1px solid #eee", borderRadius: 12, background: "#fafafa" }}>
          <div style={{ fontSize: 12, color: "#666" }}>Predicted Sales</div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>{yhat.toLocaleString()}</div>
          <MiniSparkLine points={[lag3, lag2, lag1, yhat]} />
        </div>
      )}
    </main>
  );
}

function Field({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label>
      <div style={{ fontSize: 12, color: "#555" }}>{label}</div>
      <input
        type="number"
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
      />
    </label>
  );
}

function MiniSparkLine({ points }: { points: (number | null)[] }) {
  const clean = points.map(p => (p ?? 0));
  const max = Math.max(...clean);
  const min = Math.min(...clean);
  const norm = (v: number) => (max === min ? 50 : 10 + ((v - min) / (max - min)) * 80);
  const xs = [10, 60, 110, 160];
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${100 - norm(clean[i])}`).join(" ");
  return (
    <svg width={180} height={110} style={{ marginTop: 20, display: "block" }}>
      <text x="0" y="12" fontSize="12" fill="#555">History → Forecast</text>
      <path d={path} stroke="#444" fill="none" />
      {xs.map((x, i) => (
        <circle key={i} cx={x} cy={100 - norm(clean[i])} r={3} fill={i === xs.length - 1 ? "#d00" : "#06f"} />
      ))}
      <line x1="0" x2="180" y1="100" y2="100" stroke="#eee" />
    </svg>
  );
}
