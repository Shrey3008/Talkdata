import { useState } from "react";
import { api, apiErrorMessage } from "../api/client";

export default function PinModal({ result, onClose, onPinned }) {
  const [title, setTitle] = useState(result.question.slice(0, 60));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setError("");
    try {
      await api.post("/api/dashboards/pins", {
        title,
        question: result.question,
        generated_sql: result.sql,
        chart_type: result.chart_type,
      });
      onPinned();
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <h2>Pin to dashboard</h2>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Tile title"
          maxLength={255}
          autoFocus
        />
        {error && <span className="error-text">{error}</span>}
        <div className="modal-actions">
          <button className="ghost" onClick={onClose}>Cancel</button>
          <button onClick={save} disabled={busy || !title.trim()}>
            {busy ? <span className="spinner" /> : "Pin"}
          </button>
        </div>
      </div>
    </div>
  );
}
