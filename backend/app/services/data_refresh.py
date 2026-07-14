"""Production dataset refresh — the deployed-app counterpart of the Airflow
refresh_sample_data DAG (which runs locally only; Render's free tier can't
host Airflow). Same contract: fill missing days, clean, prune, validate.
"""
import logging
import random
from datetime import date, timedelta

from sqlalchemy import text

from app.db.session import AsyncSessionLocal

log = logging.getLogger(__name__)

SHIFTS = ["Morning", "Afternoon", "Night"]
ROLLING_WINDOW_DAYS = 90
SHIFT_HOURS = 8.0


async def refresh_sample_data() -> dict:
    """Fill missing machine-days through today, clean violations, prune old rows."""
    rng = random.Random()
    summary = {"ingested": 0, "cleaned": 0, "pruned": 0}

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                text("""
                    select m.id as machine_id,
                           coalesce(max(pr.record_date), current_date - (:window)::int) as last_date
                    from machines m
                    left join production_records pr on pr.machine_id = m.id
                    group by m.id
                """),
                {"window": ROLLING_WINDOW_DAYS},
            )
        ).mappings().all()

        today = date.today()
        for row in rows:
            day = row["last_date"] + timedelta(days=1)
            while day <= today:
                for shift in SHIFTS:
                    downtime = max(0, int(rng.gauss(20, 15)))
                    units = max(0, int(rng.gauss(100, 15) - downtime * 0.8))
                    defects = min(units, max(0, int(units * rng.gauss(0.03, 0.01))))
                    await db.execute(
                        text("""
                            insert into production_records
                              (id, machine_id, record_date, shift, units_produced,
                               downtime_minutes, defect_count, throughput_rate)
                            values
                              (gen_random_uuid(), :machine_id, :day, :shift, :units,
                               :downtime, :defects, :rate)
                        """),
                        {
                            "machine_id": row["machine_id"],
                            "day": day,
                            "shift": shift,
                            "units": units,
                            "downtime": downtime,
                            "defects": defects,
                            "rate": round(units / SHIFT_HOURS, 2),
                        },
                    )
                    summary["ingested"] += 1
                day += timedelta(days=1)

        cleaned = await db.execute(
            text("""
                update production_records
                set downtime_minutes = greatest(downtime_minutes, 0),
                    units_produced = greatest(units_produced, 0),
                    defect_count = least(defect_count, greatest(units_produced, 0))
                where downtime_minutes < 0 or units_produced < 0 or defect_count > units_produced
            """)
        )
        summary["cleaned"] = cleaned.rowcount

        pruned = await db.execute(
            text("delete from production_records where record_date < current_date - (:window)::int"),
            {"window": ROLLING_WINDOW_DAYS},
        )
        summary["pruned"] = pruned.rowcount

        await db.commit()

    log.info("Data refresh complete: %s", summary)
    return summary
