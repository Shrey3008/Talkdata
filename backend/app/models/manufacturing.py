import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    machines: Mapped[list["Machine"]] = relationship(back_populates="department")


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"), nullable=False)

    department: Mapped["Department"] = relationship(back_populates="machines")
    production_records: Mapped[list["ProductionRecord"]] = relationship(back_populates="machine")


class ProductionRecord(Base):
    __tablename__ = "production_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift: Mapped[str] = mapped_column(String(20), nullable=False)
    units_produced: Mapped[int] = mapped_column(Integer, nullable=False)
    downtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    throughput_rate: Mapped[float] = mapped_column(Float, nullable=False)

    machine: Mapped["Machine"] = relationship(back_populates="production_records")
