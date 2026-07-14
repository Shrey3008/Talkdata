"""Execute validated, read-only SQL with a hard timeout and JSON-safe results."""
import datetime
import decimal
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.db.session import engine

STATEMENT_TIMEOUT_MS = 10_000


class SQLExecutionError(Exception):
    pass


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _json_safe(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


async def execute_readonly(sql: str) -> QueryResult:
    """Run inside a READ ONLY transaction with a statement timeout.

    Uses a dedicated connection (not the request session) so a rollback here
    can't expire ORM objects loaded elsewhere in the request.
    """
    async with engine.connect() as conn:
        try:
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            await conn.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
            result = await conn.execute(text(sql))
            columns = list(result.keys())
            rows = [[_json_safe(v) for v in row] for row in result.fetchall()]
        except Exception as e:  # surface DB errors to the repair loop with a clean message
            raise SQLExecutionError(str(e.__cause__ or e)) from e
        finally:
            await conn.rollback()  # nothing to commit; release the read-only txn
        return QueryResult(columns=columns, rows=rows)
