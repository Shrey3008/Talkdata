import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.dashboard import PinnedQuery
from app.models.user import User
from app.schemas.query import PinnedItem, PinRequest
from app.services.chart_selector import select_chart_type
from app.services.sql_executor import SQLExecutionError, execute_readonly
from app.services.sql_guard import SQLValidationError, validate_sql

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

MAX_PINS_PER_USER = 12


@router.get("/pins", response_model=list[PinnedItem])
async def list_pins(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PinnedQuery]:
    rows = await db.scalars(
        select(PinnedQuery)
        .where(PinnedQuery.user_id == current_user.id)
        .order_by(PinnedQuery.created_at.asc())
    )
    return list(rows)


@router.post("/pins", response_model=PinnedItem, status_code=status.HTTP_201_CREATED)
async def create_pin(
    payload: PinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PinnedQuery:
    count = len(
        (await db.scalars(select(PinnedQuery.id).where(PinnedQuery.user_id == current_user.id))).all()
    )
    if count >= MAX_PINS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pin limit reached ({MAX_PINS_PER_USER}). Unpin something first.",
        )

    # Re-validate stored SQL so only guard-approved queries can ever be pinned.
    try:
        safe_sql = validate_sql(payload.generated_sql)
    except SQLValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    pin = PinnedQuery(
        user_id=current_user.id,
        title=payload.title,
        question=payload.question,
        generated_sql=safe_sql,
        chart_type=payload.chart_type,
    )
    db.add(pin)
    await db.commit()
    await db.refresh(pin)
    return pin


@router.post("/pins/{pin_id}/run")
async def run_pin(
    pin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    pin = await db.scalar(
        select(PinnedQuery).where(PinnedQuery.id == pin_id, PinnedQuery.user_id == current_user.id)
    )
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pin not found")

    try:
        safe_sql = validate_sql(pin.generated_sql)
        result = await execute_readonly(safe_sql)
    except (SQLValidationError, SQLExecutionError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return {
        "id": str(pin.id),
        "title": pin.title,
        "question": pin.question,
        "sql": safe_sql,
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "chart_type": pin.chart_type or select_chart_type(result),
    }


@router.delete("/pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pin(
    pin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        delete(PinnedQuery).where(PinnedQuery.id == pin_id, PinnedQuery.user_id == current_user.id)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pin not found")
