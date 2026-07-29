"use client";

import { useEffect, useState, type ReactNode } from "react";
import type {
  TdHTMLAttributes,
  ThHTMLAttributes,
} from "react";


const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL
  || "http://127.0.0.1:8000";


type ModelName = "rf" | "xgb";

type ModelsResponse = {
  available_models: ModelName[];
  default_model?: ModelName;
};

type ForecastFeatures = {
  lag_1: number;
  lag_2: number;
  lag_3: number;
  month_of_year: number;
  rolling_mean_3: number;
  rolling_mean_6: number;
};

type PredictResponse = {
  target_month: string;
  prediction: number;
  model: ModelName;
  features: ForecastFeatures;
  feature_source: string;
  logged: boolean;
};

type LogRow = {
  id: number;
  model: ModelName;
  target_month: string;
  lag_1: number;
  lag_2: number;
  lag_3: number;
  month_of_year: number;
  rolling_mean_3: number;
  rolling_mean_6: number;
  prediction: number;
  created_at: string;
};


const FEATURE_LABELS: Array<
  [keyof ForecastFeatures, string]
> = [
  ["lag_1", "Previous month"],
  ["lag_2", "Two months ago"],
  ["lag_3", "Three months ago"],
  ["month_of_year", "Target month number"],
  ["rolling_mean_3", "3-month rolling mean"],
  ["rolling_mean_6", "6-month rolling mean"],
];


function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}


async function getResponseError(
  response: Response,
): Promise<string> {
  let message = `${response.status} ${response.statusText}`;

  try {
    const body = await response.json() as {
      detail?: unknown;
    };

    if (typeof body.detail === "string") {
      message = body.detail;
    }
  } catch {
    // Keep the HTTP status message when no JSON body exists.
  }

  return message;
}


function formatNumber(
  value: number,
  maximumFractionDigits = 2,
): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits,
  });
}


function formatMonth(value: string): string {
  const [year, month] = value.split("-");

  if (!year || !month) {
    return value;
  }

  return `${year}-${month}`;
}


export default function Home() {
  const [model, setModel] =
    useState<ModelName>("rf");

  const [availableModels, setAvailableModels] =
    useState<ModelName[]>(["rf"]);

  const [forecast, setForecast] =
    useState<PredictResponse | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [logs, setLogs] =
    useState<LogRow[]>([]);

  const [logLimit, setLogLimit] =
    useState(10);

  const [loadingLogs, setLoadingLogs] =
    useState(false);

  const [logError, setLogError] =
    useState("");


  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/models`,
        );

        if (!response.ok) {
          throw new Error(
            await getResponseError(response),
          );
        }

        const data =
          await response.json() as ModelsResponse;

        if (
          Array.isArray(data.available_models)
          && data.available_models.length > 0
        ) {
          setAvailableModels(
            data.available_models,
          );

          const preferredModel =
            data.default_model
            && data.available_models.includes(
              data.default_model,
            )
              ? data.default_model
              : data.available_models.includes("rf")
                ? "rf"
                : data.available_models[0];

          setModel(preferredModel);
        }
      } catch {
        // Keep Random Forest as the local default.
      }
    };

    void loadModels();
  }, []);


  const onPredict = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_BASE}/predict?model=${encodeURIComponent(model)}`,
      );

      if (!response.ok) {
        throw new Error(
          await getResponseError(response),
        );
      }

      const data =
        await response.json() as PredictResponse;

      setForecast(data);

    } catch (requestError: unknown) {
      setError(
        getErrorMessage(requestError)
        || "Forecast request failed.",
      );

      setForecast(null);

    } finally {
      setLoading(false);
    }
  };


  const onShowLogs = async () => {
    try {
      setLoadingLogs(true);
      setLogError("");

      const safeLimit = Math.min(
        100,
        Math.max(1, logLimit),
      );

      const response = await fetch(
        `${API_BASE}/logs/latest?limit=${safeLimit}`,
      );

      if (!response.ok) {
        throw new Error(
          await getResponseError(response),
        );
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error(
          "Logs endpoint returned an unexpected response.",
        );
      }

      setLogs(data as LogRow[]);

    } catch (requestError: unknown) {
      setLogError(
        getErrorMessage(requestError)
        || "Failed to fetch forecast logs.",
      );

      setLogs([]);

    } finally {
      setLoadingLogs(false);
    }
  };


  return (
    <main
      style={{
        maxWidth: 1100,
        margin: "40px auto",
        padding: "0 20px 48px",
        fontFamily:
          "system-ui, -apple-system, Segoe UI, Roboto, Arial",
      }}
    >
      <header style={{ marginBottom: 28 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: 1,
            textTransform: "uppercase",
            color: "#666",
          }}
        >
          Warehouse-driven forecasting
        </div>

        <h1
          style={{
            fontSize: 32,
            margin: "6px 0 8px",
          }}
        >
          Sales Forecast Platform v1.8
        </h1>

        <p
          style={{
            color: "#666",
            lineHeight: 1.6,
            margin: 0,
            maxWidth: 760,
          }}
        >
          Forecast the next available month using tested
          features generated in BigQuery and dbt. The API
          validates the shared feature contract, loads the
          selected model, and stores each prediction in
          PostgreSQL.
        </p>
      </header>


      <section
        style={{
          border: "1px solid #e5e5e5",
          borderRadius: 14,
          padding: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "end",
            flexWrap: "wrap",
            gap: 14,
          }}
        >
          <label>
            <div
              style={{
                fontSize: 12,
                color: "#555",
                marginBottom: 6,
              }}
            >
              Forecasting model
            </div>

            <select
              value={model}
              onChange={(event) =>
                setModel(
                  event.target.value as ModelName,
                )
              }
              style={{
                minWidth: 210,
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #ccc",
                background: "#fff",
              }}
            >
              {availableModels.map(
                (availableModel) => (
                  <option
                    key={availableModel}
                    value={availableModel}
                  >
                    {availableModel === "rf"
                      ? "Random Forest (recommended)"
                      : "XGBoost"}
                  </option>
                ),
              )}
            </select>
          </label>

          <button
            onClick={onPredict}
            disabled={
              loading
              || availableModels.length === 0
            }
            style={{
              minHeight: 42,
              padding: "10px 18px",
              borderRadius: 9,
              border: "1px solid #111",
              background: loading
                ? "#777"
                : "#111",
              color: "#fff",
              cursor: loading
                ? "not-allowed"
                : "pointer",
              fontWeight: 650,
            }}
          >
            {loading
              ? "Forecasting..."
              : "Forecast next month"}
          </button>
        </div>

        <p
          style={{
            margin: "14px 0 0",
            fontSize: 13,
            color: "#666",
          }}
        >
          No feature input is required. The six model
          features are read from
          {" "}
          <code>mart_next_month_features</code>.
        </p>

        {error && (
          <div
            style={{
              marginTop: 16,
              padding: 12,
              color: "#9b1c1c",
              background: "#fff5f5",
              border: "1px solid #ffd4d4",
              borderRadius: 8,
            }}
          >
            Error: {error}
          </div>
        )}
      </section>


      {forecast && !error && (
        <section
          style={{
            marginTop: 20,
            border: "1px solid #e5e5e5",
            borderRadius: 14,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: 20,
              background: "#fafafa",
              borderBottom: "1px solid #e5e5e5",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "start",
                flexWrap: "wrap",
                gap: 16,
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#666",
                  }}
                >
                  Forecast for{" "}
                  {formatMonth(
                    forecast.target_month,
                  )}
                </div>

                <div
                  style={{
                    marginTop: 3,
                    fontSize: 34,
                    fontWeight: 750,
                  }}
                >
                  {formatNumber(
                    forecast.prediction,
                  )}
                </div>

                <div
                  style={{
                    marginTop: 5,
                    fontSize: 13,
                    color: "#666",
                  }}
                >
                  Model:{" "}
                  {forecast.model.toUpperCase()}
                  {" · "}
                  {forecast.logged
                    ? "Saved to PostgreSQL"
                    : "Database logging failed"}
                </div>
              </div>

              <MiniSparkLine
                points={[
                  forecast.features.lag_3,
                  forecast.features.lag_2,
                  forecast.features.lag_1,
                  forecast.prediction,
                ]}
              />
            </div>
          </div>

          <div style={{ padding: 20 }}>
            <div
              style={{
                fontSize: 15,
                fontWeight: 700,
                marginBottom: 12,
              }}
            >
              Warehouse feature snapshot
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 12,
              }}
            >
              {FEATURE_LABELS.map(
                ([featureName, label]) => (
                  <FeatureCard
                    key={featureName}
                    label={label}
                    technicalName={featureName}
                    value={
                      featureName === "month_of_year"
                        ? formatNumber(
                            forecast.features[
                              featureName
                            ],
                            0,
                          )
                        : formatNumber(
                            forecast.features[
                              featureName
                            ],
                          )
                    }
                  />
                ),
              )}
            </div>

            <div
              style={{
                marginTop: 14,
                fontSize: 12,
                color: "#777",
              }}
            >
              Feature source:{" "}
              <code>
                {forecast.feature_source}
              </code>
            </div>
          </div>
        </section>
      )}


      <section style={{ marginTop: 32 }}>
        <h2
          style={{
            fontSize: 21,
            marginBottom: 6,
          }}
        >
          Recent forecast logs
        </h2>

        <p
          style={{
            color: "#666",
            marginTop: 0,
          }}
        >
          Inspect the target month, warehouse features,
          selected model, and stored prediction.
        </p>

        <div
          style={{
            display: "flex",
            alignItems: "end",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <label>
            <div
              style={{
                fontSize: 12,
                color: "#555",
                marginBottom: 6,
              }}
            >
              Number of records
            </div>

            <input
              type="number"
              min={1}
              max={100}
              value={logLimit}
              onChange={(event) =>
                setLogLimit(
                  Number(event.target.value),
                )
              }
              style={{
                width: 130,
                padding: 10,
                borderRadius: 8,
                border: "1px solid #ccc",
              }}
            />
          </label>

          <button
            onClick={onShowLogs}
            disabled={loadingLogs}
            style={{
              minHeight: 42,
              padding: "10px 18px",
              borderRadius: 9,
              border: "1px solid #222",
              background: loadingLogs
                ? "#777"
                : "#111",
              color: "#fff",
              cursor: loadingLogs
                ? "not-allowed"
                : "pointer",
            }}
          >
            {loadingLogs
              ? "Loading..."
              : "Load logs"}
          </button>
        </div>

        {logError && (
          <div
            style={{
              marginTop: 14,
              color: "#9b1c1c",
            }}
          >
            Error: {logError}
          </div>
        )}

        {logs.length > 0 && (
          <div
            style={{
              marginTop: 16,
              border: "1px solid #e5e5e5",
              borderRadius: 12,
              overflowX: "auto",
            }}
          >
            <table
              style={{
                width: "100%",
                minWidth: 1180,
                borderCollapse: "collapse",
              }}
            >
              <thead style={{ background: "#fafafa" }}>
                <tr>
                  <Th>ID</Th>
                  <Th>Created</Th>
                  <Th>Target</Th>
                  <Th>Model</Th>
                  <Th>Lag 1</Th>
                  <Th>Lag 2</Th>
                  <Th>Lag 3</Th>
                  <Th>Month</Th>
                  <Th>Rolling 3</Th>
                  <Th>Rolling 6</Th>
                  <Th>Prediction</Th>
                </tr>
              </thead>

              <tbody>
                {logs.map((row) => (
                  <tr
                    key={row.id}
                    style={{
                      borderTop:
                        "1px solid #eeeeee",
                    }}
                  >
                    <Td>{row.id}</Td>

                    <Td>
                      {new Date(
                        row.created_at,
                      ).toLocaleString()}
                    </Td>

                    <Td>
                      {formatMonth(
                        row.target_month,
                      )}
                    </Td>

                    <Td>
                      {row.model.toUpperCase()}
                    </Td>

                    <Td>
                      {formatNumber(row.lag_1)}
                    </Td>

                    <Td>
                      {formatNumber(row.lag_2)}
                    </Td>

                    <Td>
                      {formatNumber(row.lag_3)}
                    </Td>

                    <Td>
                      {row.month_of_year}
                    </Td>

                    <Td>
                      {formatNumber(
                        row.rolling_mean_3,
                      )}
                    </Td>

                    <Td>
                      {formatNumber(
                        row.rolling_mean_6,
                      )}
                    </Td>

                    <Td
                      style={{
                        fontWeight: 700,
                      }}
                    >
                      {formatNumber(
                        row.prediction,
                      )}
                    </Td>
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


function FeatureCard({
  label,
  technicalName,
  value,
}: {
  label: string;
  technicalName: string;
  value: string;
}) {
  return (
    <div
      style={{
        border: "1px solid #e8e8e8",
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: "#666",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop: 4,
          fontSize: 19,
          fontWeight: 700,
        }}
      >
        {value}
      </div>

      <code
        style={{
          display: "block",
          marginTop: 5,
          fontSize: 11,
          color: "#777",
        }}
      >
        {technicalName}
      </code>
    </div>
  );
}


function Th({
  children,
  style,
  ...rest
}: ThHTMLAttributes<HTMLTableCellElement> & {
  children: ReactNode;
}) {
  return (
    <th
      {...rest}
      style={{
        textAlign: "left",
        padding: "11px 12px",
        fontSize: 12,
        color: "#666",
        fontWeight: 650,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </th>
  );
}


function Td({
  children,
  style,
  ...rest
}: TdHTMLAttributes<HTMLTableCellElement> & {
  children: ReactNode;
}) {
  return (
    <td
      {...rest}
      style={{
        padding: "11px 12px",
        fontSize: 13,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </td>
  );
}


function MiniSparkLine({
  points,
}: {
  points: number[];
}) {
  const maximum = Math.max(...points);
  const minimum = Math.min(...points);

  const normalize = (value: number) =>
    maximum === minimum
      ? 48
      : 12
        + (
          (value - minimum)
          / (maximum - minimum)
        ) * 72;

  const xPositions = [12, 64, 116, 168];

  const path = xPositions
    .map(
      (xPosition, index) =>
        `${index === 0 ? "M" : "L"} `
        + `${xPosition} `
        + `${96 - normalize(points[index])}`,
    )
    .join(" ");

  return (
    <svg
      width={184}
      height={112}
      role="img"
      aria-label="Previous three months and forecast"
    >
      <text
        x="2"
        y="12"
        fontSize="11"
        fill="#666"
      >
        History → forecast
      </text>

      <path
        d={path}
        stroke="#444"
        strokeWidth={2}
        fill="none"
      />

      {xPositions.map(
        (xPosition, index) => (
          <circle
            key={xPosition}
            cx={xPosition}
            cy={
              96
              - normalize(points[index])
            }
            r={4}
            fill={
              index === xPositions.length - 1
                ? "#b42318"
                : "#175cd3"
            }
          />
        ),
      )}

      <line
        x1="0"
        x2="184"
        y1="100"
        y2="100"
        stroke="#e5e5e5"
      />
    </svg>
  );
}
