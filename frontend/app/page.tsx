"use client";
import { useEffect, useState, type ReactNode } from "react";
import type { ThHTMLAttributes, TdHTMLAttributes } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
type ModelName = "rf" | "xgb";

type LogRow = {
  id: number;
  model: string;
  lag1: number;
  lag2: number;
  lag3: number;
  prediction: number;
  created_at: string; // ISO string
};

export default function Home() {
  const [lag1, setLag1] = useState<number>(30000);
  const [lag2, setLag2] = useState<number>(28000);
  const [lag3, setLag3] = useState<number>(25000);
  const [model, setModel] = useState<ModelName>("rf");
  const [available, setAvailable] = useState<ModelName[]>(["rf"]);
  const [yhat, setYhat] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  // logs
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [logLimit, setLogLimit] = useState<number>(10);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [logErr, setLogErr] = useState<string>("");

  // fetch available models
  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d.available_models) && d.available_models.length) {
          setAvailable(d.available_models);
          setModel(d.available_models.includes("rf") ? "rf" : (d.available_models[0] as ModelName));
        }
      })
      .catch(() => {});
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

  const onShowLogs = async () => {
    try {
      setLoadingLogs(true);
      setLogErr("");
      const url = `${API_BASE}/logs/latest?limit=${logLimit}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
      const data: LogRow[] = await resp.json();
      setLogs(data);
    } catch (e: any) {
      setLogErr(e.message || "Failed to fetch logs");
      setLogs([]);
    } finally {
      setLoadingLogs(false);
    }
  };

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial" }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>Sales Forecast — v1.4 Frontend + v1.5 Logging</h1>
      <p style={{ color: "#666", marginBottom: 20 }}>
        Select a model, input the last 3 months’ sales, get a prediction, and view recent API logs stored in PostgreSQL.
      </p>

      {/* Model selector */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: "#555", marginBottom: 6 }}>Model</div>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value as ModelName)}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
        >
          {available.map((m) => (
            <option key={m} value={m}>
              {m === "rf" ? "RandomForest (rf)" : "XGBoost (xgb)"}
            </option>
          ))}
        </select>
      </div>

      {/* Lags */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <Field label="lag1 (last month)" value={lag1} onChange={(v) => setLag1(v)} />
        <Field label="lag2 (2 months ago)" value={lag2} onChange={(v) => setLag2(v)} />
        <Field label="lag3 (3 months ago)" value={lag3} onChange={(v) => setLag3(v)} />
      </div>

      <button
        onClick={onPredict}
        disabled={loading}
        style={{
          marginTop: 16,
          padding: "10px 16px",
          borderRadius: 10,
          border: "1px solid #222",
          background: loading ? "#777" : "#111",
          color: "#fff",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
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

      {/* Logs */}
      <section style={{ marginTop: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div>
            <div style={{ fontSize: 12, color: "#555" }}>Show latest N logs</div>
            <input
              type="number"
              min={1}
              max={100}
              value={logLimit}
              onChange={(e) => setLogLimit(Number(e.target.value))}
              style={{ width: 120, padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
            />
          </div>

          <button
            onClick={onShowLogs}
            disabled={loadingLogs}
            style={{
              padding: "10px 16px",
              borderRadius: 10,
              border: "1px solid #222",
              background: loadingLogs ? "#777" : "#111",
              color: "#fff",
              cursor: loadingLogs ? "not-allowed" : "pointer",
              height: 44,
              alignSelf: "end",
            }}
          >
            {loadingLogs ? "Loading..." : "Show Logs"}
          </button>

          {logErr && <div style={{ color: "#b00020" }}>Error: {logErr}</div>}
        </div>

        {logs.length > 0 && (
          <div style={{ marginTop: 16, border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ background: "#fafafa" }}>
                <tr>
                  <Th>ID</Th>
                  <Th>Time (UTC)</Th>
                  <Th>Model</Th>
                  <Th>lag1</Th>
                  <Th>lag2</Th>
                  <Th>lag3</Th>
                  <Th>Prediction</Th>
                </tr>
              </thead>
              <tbody>
                {logs.map((r) => (
                  <tr key={r.id} style={{ borderTop: "1px solid #eee" }}>
                    <Td>{r.id}</Td>
                    <Td>{new Date(r.created_at).toLocaleString()}</Td>
                    <Td>{r.model.toUpperCase()}</Td>
                    <Td>{Math.round(r.lag1)}</Td>
                    <Td>{Math.round(r.lag2)}</Td>
                    <Td>{Math.round(r.lag3)}</Td>
                    <Td style={{ fontWeight: 700 }}>{Math.round(r.prediction).toLocaleString()}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
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
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
      />
    </label>
  );
}

/** Accept and forward native <th> props (incl. style) */
function Th({ children, style, ...rest }: ThHTMLAttributes<HTMLTableCellElement> & { children: ReactNode }) {
  return (
    <th
      {...rest}
      style={{
        textAlign: "left",
        padding: "10px 12px",
        fontSize: 12,
        color: "#666",
        fontWeight: 600,
        ...(style || {}),
      }}
    >
      {children}
    </th>
  );
}

/** Accept and forward native <td> props (incl. style) */
function Td({ children, style, ...rest }: TdHTMLAttributes<HTMLTableCellElement> & { children: ReactNode }) {
  return (
    <td
      {...rest}
      style={{ padding: "10px 12px", fontSize: 13, ...(style || {}) }}
    >
      {children}
    </td>
  );
}

function MiniSparkLine({ points }: { points: (number | null)[] }) {
  const clean = points.map((p) => p ?? 0);
  const max = Math.max(...clean);
  const min = Math.min(...clean);
  const norm = (v: number) => (max === min ? 50 : 10 + ((v - min) / (max - min)) * 80);
  const xs = [10, 60, 110, 160];
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${100 - norm(clean[i])}`).join(" ");
  return (
    <svg width={180} height={110} style={{ marginTop: 20, display: "block" }}>
      <text x="0" y="12" fontSize="12" fill="#555">
        History → Forecast
      </text>
      <path d={path} stroke="#444" fill="none" />
      {xs.map((x, i) => (
        <circle key={i} cx={x} cy={100 - norm(clean[i])} r={3} fill={i === xs.length - 1 ? "#d00" : "#06f"} />
      ))}
      <line x1="0" x2="180" y1="100" y2="100" stroke="#eee" />
    </svg>
  );
}
