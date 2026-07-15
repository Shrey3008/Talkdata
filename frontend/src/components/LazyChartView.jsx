import { Suspense, lazy } from "react";

// recharts is ~2/3 of the bundle; splitting it means login/dashboard shells
// load fast and the chart chunk arrives with the first result.
const ChartView = lazy(() => import("./ChartView"));

export default function LazyChartView(props) {
  return (
    <Suspense fallback={<p className="muted">Loading chart…</p>}>
      <ChartView {...props} />
    </Suspense>
  );
}
