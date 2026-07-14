"""Curated, embeddable descriptions of the queryable sample-data schema.

Each document describes one table or one column in natural language, including
synonyms users are likely to type ("outage" for downtime, "scrap" for defects),
so that question embeddings land near the right schema chunks.

Only the manufacturing sample tables are described here — app tables (users,
query_history, pinned_queries, schema_embeddings) are deliberately excluded so
the NL->SQL layer never sees or queries them.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaDoc:
    table_name: str
    column_name: str | None  # None => table-level summary
    content: str


SCHEMA_DOCS: list[SchemaDoc] = [
    # ---- departments ----
    SchemaDoc(
        "departments",
        None,
        "Table departments: the factory's departments / areas / sections of the plant. "
        "One row per department. Columns: id (uuid primary key), name (text). "
        "Joins: machines.department_id -> departments.id.",
    ),
    SchemaDoc(
        "departments",
        "name",
        "Column departments.name (text): department name. Values: Assembly, Welding, "
        "Painting, Packaging, Quality Control. Use for grouping or filtering results "
        "by department, area, team, or section of the factory.",
    ),
    # ---- machines ----
    SchemaDoc(
        "machines",
        None,
        "Table machines: individual machines / equipment / assets on the factory floor. "
        "One row per physical machine. Columns: id (uuid primary key), name (text), "
        "machine_type (text), department_id (uuid foreign key -> departments.id). "
        "Joins: production_records.machine_id -> machines.id; "
        "machines.department_id -> departments.id.",
    ),
    SchemaDoc(
        "machines",
        "name",
        "Column machines.name (text): human-readable machine name like 'Spot Welder #1' "
        "or 'Paint Booth #2'. Use when the user asks about a specific machine, equipment, "
        "or asset by name.",
    ),
    SchemaDoc(
        "machines",
        "machine_type",
        "Column machines.machine_type (text): the kind/category of machine. Values include "
        "Conveyor Line, Robotic Arm, Assembly Line, Spot Welder, Arc Welder, Paint Booth, "
        "Spray Robot, Case Packer, Palletizer, Inspection Station, X-Ray Scanner. "
        "Use for grouping by machine type or equipment category.",
    ),
    SchemaDoc(
        "machines",
        "department_id",
        "Column machines.department_id (uuid): foreign key to departments.id. Join through "
        "this to relate machines or production data to a department.",
    ),
    # ---- production_records ----
    SchemaDoc(
        "production_records",
        None,
        "Table production_records: the core fact table of factory operations data. One row "
        "per machine per shift per day for the last 90 days. Columns: id (uuid), machine_id "
        "(uuid foreign key -> machines.id), record_date (date), shift (text), units_produced "
        "(integer), downtime_minutes (integer), defect_count (integer), throughput_rate (float). "
        "Use for questions about production, output, performance, efficiency, downtime, "
        "defects, quality, throughput, or trends over time. "
        "Joins: production_records.machine_id -> machines.id -> departments.",
    ),
    SchemaDoc(
        "production_records",
        "record_date",
        "Column production_records.record_date (date): the calendar day of the record. "
        "Use for time filters (last week, last 30 days, this month, a specific date) and "
        "time-series trends. Data covers roughly the last 90 days.",
    ),
    SchemaDoc(
        "production_records",
        "shift",
        "Column production_records.shift (text): work shift of the record. Values: Morning, "
        "Afternoon, Night. Use when comparing shifts or filtering to a specific shift.",
    ),
    SchemaDoc(
        "production_records",
        "units_produced",
        "Column production_records.units_produced (integer): number of units / parts / items "
        "produced (output, production volume, quantity made) by a machine during one shift.",
    ),
    SchemaDoc(
        "production_records",
        "downtime_minutes",
        "Column production_records.downtime_minutes (integer): minutes the machine was down, "
        "idle, stopped, broken, or under maintenance during the shift. Synonyms: outage, "
        "downtime, breakdown time, stoppage, lost time, availability loss.",
    ),
    SchemaDoc(
        "production_records",
        "defect_count",
        "Column production_records.defect_count (integer): number of defective / faulty / "
        "rejected / scrapped units in the shift. Use for quality questions, defect rate "
        "(defect_count divided by units_produced), scrap, rework, or failure analysis.",
    ),
    SchemaDoc(
        "production_records",
        "throughput_rate",
        "Column production_records.throughput_rate (float): units produced per hour over the "
        "8-hour shift. Use for throughput, speed, output rate, efficiency, or productivity "
        "comparisons between machines, departments, or shifts.",
    ),
]
