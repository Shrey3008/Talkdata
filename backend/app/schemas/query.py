import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart_type: str
    history_id: uuid.UUID
    was_repaired: bool = False


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    generated_sql: str
    chart_type: str | None
    result_row_count: int | None
    created_at: datetime


class PinRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    question: str
    generated_sql: str
    chart_type: str | None = None


class PinnedItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    question: str
    generated_sql: str
    chart_type: str | None
    created_at: datetime
