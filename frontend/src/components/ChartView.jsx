import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// dataviz reference palette, dark-mode categorical slots (validated)
const SERIES = ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9", "#e66767"];
const INK = { primary: "#ffffff", secondary: "#c3c2b7", muted: "#898781" };
const GRID = "#2c2c2a";
const SURFACE = "#1a1a19";

const tooltipStyle = {
  background: "#222221",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8,
  fontSize: 12.5,
  color: INK.secondary,
};

const fmt = (v) => {
  if (typeof v !== "number") return v;
  if (Math.abs(v) >= 1000) return v.toLocaleString();
  if (Number.isInteger(v)) return v;
  // enough precision that nearby axis ticks stay distinct
  return Number(v.toPrecision(3)).toString();
};

function prettyLabel(col) {
  return col.replaceAll("_", " ");
}

function toObjects(columns, rows) {
  return rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
}

export default function ChartView({ chartType, columns, rows }) {
  if (chartType === "table" || rows.length === 0) return null;

  if (chartType === "stat") {
    return (
      <div className="stat-tile">
        <span className="stat-label">{prettyLabel(columns[0])}</span>
        <span className="stat-value">{fmt(rows[0][0])}</span>
      </div>
    );
  }

  const data = toObjects(columns, rows);
  const [xKey, ...valueKeys] = columns;
  const numericKeys = valueKeys.filter((k) => data.every((d) => d[k] === null || typeof d[k] === "number"));
  if (numericKeys.length === 0) return null;
  const multiSeries = numericKeys.length > 1;

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: INK.muted, fontSize: 11 }} stroke={GRID}
            tickFormatter={(v) => (typeof v === "string" ? v.slice(5) : v)} />
          <YAxis tick={{ fill: INK.muted, fontSize: 11 }} stroke={GRID} tickFormatter={fmt} width={52} />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: INK.primary }} formatter={(v) => fmt(v)} />
          {multiSeries && <Legend wrapperStyle={{ fontSize: 12, color: INK.secondary }} />}
          {numericKeys.map((key, i) => (
            <Line
              key={key}
              dataKey={key}
              name={prettyLabel(key)}
              stroke={SERIES[i % SERIES.length]}
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2, stroke: SURFACE, fill: SERIES[i % SERIES.length] }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "bar") {
    return (
      <ResponsiveContainer width="100%" height={Math.max(260, Math.min(400, data.length * 34))}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 32, bottom: 4, left: 8 }}>
          <CartesianGrid stroke={GRID} strokeWidth={1} horizontal={false} />
          <XAxis type="number" tick={{ fill: INK.muted, fontSize: 11 }} stroke={GRID} tickFormatter={fmt} />
          <YAxis type="category" dataKey={xKey} width={150}
            tick={{ fill: INK.secondary, fontSize: 12 }} stroke={GRID} />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: INK.primary }}
            formatter={(v) => fmt(v)} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
          {multiSeries && <Legend wrapperStyle={{ fontSize: 12, color: INK.secondary }} />}
          {numericKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              name={prettyLabel(key)}
              fill={multiSeries ? SERIES[i % SERIES.length] : SERIES[0]}
              radius={[0, 4, 4, 0]}
              maxBarSize={24}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "pie") {
    const valueKey = numericKeys[0];
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={xKey}
            innerRadius={62}
            outerRadius={100}
            paddingAngle={2}
            stroke={SURFACE}
            strokeWidth={2}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={SERIES[i % SERIES.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmt(v)} />
          <Legend wrapperStyle={{ fontSize: 12, color: INK.secondary }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return null;
}
