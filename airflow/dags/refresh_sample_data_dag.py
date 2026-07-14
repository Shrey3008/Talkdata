"""Daily ETL for the TalkData manufacturing sample dataset.

Simulates a nightly ingest from factory systems, then cleans and validates:

  extract_backlog -> generate_records -> clean_data -> prune_history -> quality_checks

- extract_backlog: find which (machine, day) slots are missing since the last load
- generate_records: synthesize those shifts' production data (the "ingest")
- clean_data: repair rule violations (negative metrics, impossible rates)
- prune_history: keep a rolling 90-day window so the dataset never grows unbounded
- quality_checks: hard assertions — the DAG fails loudly if the data is bad
"""
from __future__ import annotations

import logging
import os
import random
from datetime import date, timedelta

import pendulum
from airflow.decorators import dag, task

log = logging.getLogger(__name__)

SHIFTS = ["Morning", "Afternoon", "Night"]
ROLLING_WINDOW_DAYS = 90
SHIFT_HOURS = 8.0


def _engine():
    """Sync SQLAlchemy engine for the TalkData app database (Supabase)."""
    from sqlalchemy import create_engine

    url = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    return create_engine(url, pool_pre_ping=True)


@dag(
    dag_id="refresh_sample_data",
    description="Nightly ingest + clean + prune + validate for the manufacturing sample dataset",
    schedule="0 3 * * *",  # 03:00 UTC daily
    start_date=pendulum.datetime(2026, 7, 1, tz="UTC"),
    catchup=False,
    default_args={"retries": 1, "retry_delay": pendulum.duration(minutes=5)},
    tags=["talkdata", "etl"],
)
def refresh_sample_data():
    @task
    def extract_backlog() -> list[dict]:
        """Return (machine_id, day) slots missing between the last load and today."""
        from sqlalchemy import text

        with _engine().connect() as conn:
            rows = conn.execute(
                text("""
                    select m.id::text as machine_id,
                           coalesce(max(pr.record_date), current_date - :window) as last_date
                    from machines m
                    left join production_records pr on pr.machine_id = m.id
                    group by m.id
                """),
                {"window": ROLLING_WINDOW_DAYS},
            ).mappings().all()

        today = date.today()
        backlog = []
        for row in rows:
            day = row["last_date"] + timedelta(days=1)
            while day <= today:
                backlog.append({"machine_id": row["machine_id"], "day": day.isoformat()})
                day += timedelta(days=1)
        log.info("Backlog: %d machine-days to ingest", len(backlog))
        return backlog

    @task
    def generate_records(backlog: list[dict]) -> int:
        """Synthesize production records for missing slots (the simulated ingest).

        A small share of rows is generated dirty (negative downtime, null defects)
        on purpose so clean_data has real work to do — mirroring a raw feed.
        """
        from sqlalchemy import text

        if not backlog:
            log.info("Nothing to ingest.")
            return 0

        rng = random.Random()
        inserted = 0
        with _engine().begin() as conn:
            for slot in backlog:
                for shift in SHIFTS:
                    downtime = max(0, int(rng.gauss(20, 15)))
                    units = max(0, int(rng.gauss(100, 15) - downtime * 0.8))
                    defects = max(0, int(units * rng.gauss(0.03, 0.01)))
                    # ~3% of raw rows arrive dirty, as real feeds do
                    if rng.random() < 0.03:
                        downtime = -downtime if downtime else -5
                    conn.execute(
                        text("""
                            insert into production_records
                              (id, machine_id, record_date, shift, units_produced,
                               downtime_minutes, defect_count, throughput_rate)
                            values
                              (gen_random_uuid(), :machine_id, :day, :shift, :units,
                               :downtime, :defects, :rate)
                        """),
                        {
                            "machine_id": slot["machine_id"],
                            "day": slot["day"],
                            "shift": shift,
                            "units": units,
                            "downtime": downtime,
                            "defects": defects,
                            "rate": round(units / SHIFT_HOURS, 2),
                        },
                    )
                    inserted += 1
        log.info("Ingested %d raw records", inserted)
        return inserted

    @task
    def clean_data() -> dict:
        """Repair rule violations in place; report what was fixed."""
        from sqlalchemy import text

        fixes = {}
        with _engine().begin() as conn:
            fixes["negative_downtime"] = conn.execute(
                text("update production_records set downtime_minutes = 0 where downtime_minutes < 0")
            ).rowcount
            fixes["negative_units"] = conn.execute(
                text("update production_records set units_produced = 0 where units_produced < 0")
            ).rowcount
            fixes["defects_gt_units"] = conn.execute(
                text("""
                    update production_records set defect_count = units_produced
                    where defect_count > units_produced
                """)
            ).rowcount
            fixes["stale_throughput"] = conn.execute(
                text("""
                    update production_records
                    set throughput_rate = round((units_produced / :hours)::numeric, 2)
                    where abs(throughput_rate - units_produced / :hours) > 0.01
                """),
                {"hours": SHIFT_HOURS},
            ).rowcount
        log.info("Cleaning fixes applied: %s", fixes)
        return fixes

    @task
    def prune_history() -> int:
        """Keep a rolling window so the demo dataset stays a constant size."""
        from sqlalchemy import text

        with _engine().begin() as conn:
            deleted = conn.execute(
                text("delete from production_records where record_date < current_date - :window"),
                {"window": ROLLING_WINDOW_DAYS},
            ).rowcount
        log.info("Pruned %d records older than %d days", deleted, ROLLING_WINDOW_DAYS)
        return deleted

    @task
    def quality_checks() -> dict:
        """Hard gates — raise (fail the DAG) if the dataset violates its contract."""
        from sqlalchemy import text

        with _engine().connect() as conn:
            stats = conn.execute(
                text("""
                    select count(*) as total,
                           count(*) filter (where downtime_minutes < 0) as neg_downtime,
                           count(*) filter (where units_produced < 0) as neg_units,
                           count(*) filter (where defect_count > units_produced) as bad_defects,
                           count(*) filter (where record_date > current_date) as future_rows,
                           count(distinct machine_id) as machines_covered,
                           max(record_date) as latest
                    from production_records
                """)
            ).mappings().one()
            machine_count = conn.execute(text("select count(*) from machines")).scalar()

        checks = dict(stats)
        checks["latest"] = str(checks["latest"])
        log.info("Quality stats: %s", checks)

        assert stats["total"] > 0, "production_records is empty"
        assert stats["neg_downtime"] == 0, f"{stats['neg_downtime']} rows with negative downtime"
        assert stats["neg_units"] == 0, f"{stats['neg_units']} rows with negative units"
        assert stats["bad_defects"] == 0, f"{stats['bad_defects']} rows with defects > units"
        assert stats["future_rows"] == 0, f"{stats['future_rows']} rows dated in the future"
        assert stats["machines_covered"] == machine_count, (
            f"only {stats['machines_covered']}/{machine_count} machines have records"
        )
        assert stats["latest"] == date.today(), "dataset is not current through today"
        return checks

    backlog = extract_backlog()
    ingested = generate_records(backlog)
    cleaned = clean_data()
    pruned = prune_history()
    ingested >> cleaned >> pruned >> quality_checks()


refresh_sample_data()
