import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import ChartView from "../components/LazyChartView";
import ResultsTable from "../components/ResultsTable";

function PinCard({ pin, onUnpin }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.post(`/api/dashboards/pins/${pin.id}/run`)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((err) => { if (!cancelled) setError(apiErrorMessage(err)); });
    return () => { cancelled = true; };
  }, [pin.id]);

  return (
    <div className="card panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 12 }}>
        <div>
          <div className="pin-card-title">{pin.title}</div>
          <div className="pin-q">{pin.question}</div>
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          {data && data.chart_type !== "table" && (
            <button className="ghost" onClick={() => setShowTable((v) => !v)}>
              {showTable ? "Chart" : "Table"}
            </button>
          )}
          <button className="danger-ghost" onClick={() => onUnpin(pin.id)}>Unpin</button>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && (showTable || data.chart_type === "table" ? (
        <ResultsTable columns={data.columns} rows={data.rows} />
      ) : (
        <ChartView chartType={data.chart_type} columns={data.columns} rows={data.rows} />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [pins, setPins] = useState(null);

  useEffect(() => {
    api.get("/api/dashboards/pins").then((res) => setPins(res.data)).catch(() => setPins([]));
  }, []);

  async function unpin(id) {
    await api.delete(`/api/dashboards/pins/${id}`);
    setPins((prev) => prev.filter((p) => p.id !== id));
  }

  if (pins === null) return <div className="dash-wrap"><p className="muted">Loading…</p></div>;

  return (
    <div className="dash-wrap">
      <div className="dash-inner">
        <div className="dash-head">
          <h1>Dashboard</h1>
          <span className="muted">{pins.length} pinned {pins.length === 1 ? "query" : "queries"}</span>
        </div>
        {pins.length === 0 ? (
          <div className="card dash-empty">
            <p>Nothing pinned yet.</p>
            <p>Ask a question in the <Link to="/" style={{ color: "var(--accent)" }}>workspace</Link> and hit “Pin” to build your dashboard.</p>
          </div>
        ) : (
          <div className="dash-grid">
            {pins.map((pin) => <PinCard key={pin.id} pin={pin} onUnpin={unpin} />)}
          </div>
        )}
      </div>
    </div>
  );
}
