from app.services.chart_selector import select_chart_type
from app.services.sql_executor import QueryResult


def _result(columns, rows):
    return QueryResult(columns=columns, rows=rows)


def test_single_value_is_stat():
    assert select_chart_type(_result(["total"], [[42]])) == "stat"


def test_empty_is_table():
    assert select_chart_type(_result(["a", "b"], [])) == "table"


def test_time_series_is_line():
    rows = [[f"2026-07-{d:02d}", d * 10] for d in range(1, 15)]
    assert select_chart_type(_result(["record_date", "units"], rows)) == "line"


def test_categorical_is_bar():
    rows = [[f"Machine {i}", i * 100] for i in range(10)]
    assert select_chart_type(_result(["name", "total_units"], rows)) == "bar"


def test_small_part_to_whole_is_pie():
    rows = [["Assembly", 300], ["Welding", 200], ["Painting", 100]]
    assert select_chart_type(_result(["department", "total_downtime"], rows)) == "pie"


def test_averages_never_pie():
    """Averages/rates are not parts of a whole — pie would misrepresent them."""
    rows = [["Morning", 10.16], ["Night", 10.15], ["Afternoon", 10.15]]
    assert select_chart_type(_result(["shift", "average_throughput_rate"], rows)) == "bar"


def test_rate_columns_never_pie():
    rows = [["Assembly", 0.03], ["Welding", 0.02]]
    assert select_chart_type(_result(["department", "defect_rate"], rows)) == "bar"


def test_negative_values_never_pie():
    rows = [["A", 5], ["B", -3]]
    assert select_chart_type(_result(["grp", "delta_total"], rows)) == "bar"


def test_too_many_slices_is_bar():
    rows = [[f"Dept {i}", i] for i in range(8)]
    assert select_chart_type(_result(["dept", "total_count"], rows)) == "bar"


def test_no_numeric_columns_is_table():
    rows = [["Assembly", "Morning"], ["Welding", "Night"]]
    assert select_chart_type(_result(["dept", "shift"], rows)) == "table"


def test_wide_categorical_falls_back_to_table():
    rows = [[f"M{i}", i, i * 2] for i in range(40)]
    assert select_chart_type(_result(["m", "a_total", "b_total"], rows)) == "table"
