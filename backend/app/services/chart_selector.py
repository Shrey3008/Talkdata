"""Pick a chart type from the shape of a query result.

Heuristics:
- 1 row x 1 col            -> stat (big number, no chart)
- date/time first column   -> line (time series)
- 2 cols, few categories   -> pie if values look like parts of a whole, else bar
- categorical + numeric(s) -> bar
- anything else            -> table only
"""
import re
from typing import Any

from app.services.sql_executor import QueryResult

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# Column names that signal a non-additive measure: slices of these are not
# parts of a whole, so a pie chart would misrepresent them.
NON_ADDITIVE_RE = re.compile(r"avg|average|mean|median|rate|ratio|pct|percent|per_|min_|max_", re.IGNORECASE)


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_dateish(value: Any) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


def select_chart_type(result: QueryResult) -> str:
    if result.row_count == 0:
        return "table"
    if result.row_count == 1 and len(result.columns) == 1:
        return "stat"
    if len(result.columns) < 2:
        return "table"

    first_col = [row[0] for row in result.rows]
    numeric_cols = [
        i for i in range(1, len(result.columns))
        if all(_is_numeric(row[i]) or row[i] is None for row in result.rows)
    ]
    if not numeric_cols:
        return "table"

    if all(_is_dateish(v) for v in first_col):
        return "line"

    if all(isinstance(v, str) for v in first_col):
        # Pie only for a single numeric series that plausibly sums to a whole:
        # few slices, all non-negative, and not an average/rate-style measure.
        if (
            len(result.columns) == 2
            and 2 <= result.row_count <= 6
            and not NON_ADDITIVE_RE.search(result.columns[1])
        ):
            values = [row[1] for row in result.rows if row[1] is not None]
            if values and all(_is_numeric(v) and v >= 0 for v in values):
                return "pie"
        if result.row_count <= 30:
            return "bar"

    return "table"
