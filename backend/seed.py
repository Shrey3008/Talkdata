"""Seed a realistic manufacturing sample dataset (departments, machines,
90 days x 3 shifts of production_records) into the configured database.

Usage: python seed.py
Idempotent: skips seeding if departments already exist.
"""
import asyncio
import random
from datetime import date, timedelta

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Department, Machine, ProductionRecord

random.seed(42)

DEPARTMENTS = {
    "Assembly": ["Conveyor Line", "Robotic Arm", "Assembly Line"],
    "Welding": ["Spot Welder", "Arc Welder"],
    "Painting": ["Paint Booth", "Spray Robot"],
    "Packaging": ["Case Packer", "Palletizer"],
    "Quality Control": ["Inspection Station", "X-Ray Scanner"],
}

SHIFTS = ["Morning", "Afternoon", "Night"]
DAYS_OF_HISTORY = 90


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Department).limit(1))
        if existing:
            print("Departments already exist — skipping seed.")
            return

        departments: dict[str, Department] = {}
        for dept_name in DEPARTMENTS:
            dept = Department(name=dept_name)
            db.add(dept)
            departments[dept_name] = dept
        await db.flush()

        machines: list[Machine] = []
        for dept_name, machine_types in DEPARTMENTS.items():
            for machine_type in machine_types:
                for unit in range(1, random.randint(2, 3) + 1):
                    machine = Machine(
                        name=f"{machine_type} #{unit}",
                        machine_type=machine_type,
                        department_id=departments[dept_name].id,
                    )
                    db.add(machine)
                    machines.append(machine)
        await db.flush()

        start_date = date.today() - timedelta(days=DAYS_OF_HISTORY)
        records = []
        for machine in machines:
            base_throughput = random.uniform(70, 130)
            base_defect_rate = random.uniform(0.01, 0.05)
            for day_offset in range(DAYS_OF_HISTORY):
                record_date = start_date + timedelta(days=day_offset)
                for shift in SHIFTS:
                    downtime = max(0, int(random.gauss(20, 15)))
                    units_produced = max(0, int(random.gauss(base_throughput, 12) - downtime * 0.8))
                    defect_count = max(0, int(units_produced * random.gauss(base_defect_rate, 0.01)))
                    throughput_rate = round(units_produced / 8.0, 2)  # units per hour, 8h shift

                    records.append(
                        ProductionRecord(
                            machine_id=machine.id,
                            record_date=record_date,
                            shift=shift,
                            units_produced=units_produced,
                            downtime_minutes=downtime,
                            defect_count=defect_count,
                            throughput_rate=throughput_rate,
                        )
                    )

        db.add_all(records)
        await db.commit()
        print(
            f"Seeded {len(departments)} departments, {len(machines)} machines, "
            f"{len(records)} production records."
        )


if __name__ == "__main__":
    asyncio.run(seed())
