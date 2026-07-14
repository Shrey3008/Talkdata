export default function ResultsTable({ columns, rows }) {
  if (rows.length === 0) return <p className="muted">No rows returned.</p>;

  const numeric = columns.map((_, i) =>
    rows.every((r) => r[i] === null || typeof r[i] === "number")
  );

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c, i) => (
              <th key={c} className={numeric[i] ? "num" : ""}>{c.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((v, ci) => (
                <td key={ci} className={numeric[ci] ? "num" : ""}>
                  {v === null ? "—" : typeof v === "number" ? v.toLocaleString() : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
