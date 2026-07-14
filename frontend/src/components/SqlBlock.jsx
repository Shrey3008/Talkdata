import { useState } from "react";

export default function SqlBlock({ sql, wasRepaired }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="card sql-block">
      <div className="sql-head">
        <span>
          Generated SQL
          {wasRepaired && <span className="repaired-tag"> · auto-repaired</span>}
        </span>
        <button type="button" className="copy" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>{sql}</pre>
    </div>
  );
}
