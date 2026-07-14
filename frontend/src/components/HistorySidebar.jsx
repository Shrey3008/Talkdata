export default function HistorySidebar({ items, onSelect, onDelete }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">Query history</div>
      <div className="sidebar-list">
        {items.length === 0 && (
          <p className="sidebar-empty">Questions you ask will appear here.</p>
        )}
        {items.map((h) => (
          <div key={h.id} className="hist-item" onClick={() => onSelect(h)}>
            <span className="q">{h.question}</span>
            <span className="meta">
              {new Date(h.created_at).toLocaleString([], {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
              })}
              {h.result_row_count != null && ` · ${h.result_row_count} rows`}
            </span>
            <button
              className="del"
              title="Delete"
              onClick={(e) => { e.stopPropagation(); onDelete(h.id); }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
