import { useEffect, useRef, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import ChartView from "../components/LazyChartView";
import HistorySidebar from "../components/HistorySidebar";
import PinModal from "../components/PinModal";
import ResultsTable from "../components/ResultsTable";
import SqlBlock from "../components/SqlBlock";

const SUGGESTIONS = [
  "Which department has the most downtime?",
  "Daily units produced over the last 2 weeks",
  "Defect rate by machine type",
  "Average throughput per shift",
  "Top 5 machines by defect count this month",
];

export default function WorkspacePage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);
  const [showPin, setShowPin] = useState(false);
  const [toast, setToast] = useState("");
  const textareaRef = useRef(null);

  async function loadHistory() {
    try {
      const { data } = await api.get("/api/history");
      setHistory(data);
    } catch { /* sidebar is non-critical */ }
  }

  useEffect(() => { loadHistory(); }, []);

  async function ask(q) {
    const text = (q ?? question).trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/api/query", { question: text });
      setResult(data);
      loadHistory();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function rerunFromHistory(h) {
    setQuestion(h.question);
    await ask(h.question);
  }

  async function deleteHistory(id) {
    try {
      await api.delete(`/api/history/${id}`);
      setHistory((prev) => prev.filter((h) => h.id !== id));
    } catch { /* ignore */ }
  }

  function notify(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 2200);
  }

  return (
    <>
      <HistorySidebar items={history} onSelect={rerunFromHistory} onDelete={deleteHistory} />
      <div className="workspace">
        <div className="workspace-inner">
          <form
            className="query-form"
            onSubmit={(e) => { e.preventDefault(); ask(); }}
          >
            <textarea
              ref={textareaRef}
              placeholder="Ask a question about your factory data…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  ask();
                }
              }}
            />
            <button disabled={busy || !question.trim()}>
              {busy ? <span className="spinner" /> : "Ask"}
            </button>
          </form>

          {!result && !error && (
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => { setQuestion(s); ask(s); }}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {error && <p className="error-text">{error}</p>}

          {result && (
            <div className="result-block">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
                <span className="result-q">{result.question}</span>
                <button className="ghost" onClick={() => setShowPin(true)}>Pin</button>
              </div>

              <SqlBlock sql={result.sql} wasRepaired={result.was_repaired} />

              {result.chart_type !== "table" && (
                <div className="card panel">
                  <div className="panel-title">
                    <span>Chart</span>
                    <span className="muted" style={{ textTransform: "none", letterSpacing: 0 }}>
                      auto: {result.chart_type}
                    </span>
                  </div>
                  <ChartView
                    chartType={result.chart_type}
                    columns={result.columns}
                    rows={result.rows}
                  />
                </div>
              )}

              <div className="card panel">
                <div className="panel-title">
                  <span>Results</span>
                  <span className="muted" style={{ textTransform: "none", letterSpacing: 0 }}>
                    {result.row_count} row{result.row_count === 1 ? "" : "s"}
                  </span>
                </div>
                <ResultsTable columns={result.columns} rows={result.rows} />
              </div>
            </div>
          )}
        </div>
      </div>

      {showPin && result && (
        <PinModal
          result={result}
          onClose={() => setShowPin(false)}
          onPinned={() => notify("Pinned to dashboard")}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
