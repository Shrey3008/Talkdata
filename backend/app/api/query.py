from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.query_history import QueryHistory
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.services.chart_selector import select_chart_type
from app.services.llm_service import generate_sql, repair_sql
from app.services.rag_service import format_context_for_prompt, retrieve_schema_context
from app.services.sql_executor import SQLExecutionError, execute_readonly
from app.services.sql_guard import SQLValidationError, validate_sql

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def run_query(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    # 1. RAG: retrieve relevant schema context for the question
    docs = await retrieve_schema_context(db, payload.question)
    schema_context = format_context_for_prompt(docs)

    # 2. Generate SQL, validate, execute — with one repair round-trip on failure
    raw_sql = await generate_sql(payload.question, schema_context)
    was_repaired = False
    try:
        safe_sql = validate_sql(raw_sql)
        result = await execute_readonly(safe_sql)
    except (SQLValidationError, SQLExecutionError) as first_error:
        raw_sql = await repair_sql(payload.question, schema_context, raw_sql, str(first_error))
        try:
            safe_sql = validate_sql(raw_sql)
            result = await execute_readonly(safe_sql)
            was_repaired = True
        except (SQLValidationError, SQLExecutionError) as second_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not produce a valid query for this question: {second_error}",
            )

    # 3. Chart selection + history
    chart_type = select_chart_type(result)
    history = QueryHistory(
        user_id=current_user.id,
        question=payload.question,
        generated_sql=safe_sql,
        chart_type=chart_type,
        result_row_count=result.row_count,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    return QueryResponse(
        question=payload.question,
        sql=safe_sql,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        chart_type=chart_type,
        history_id=history.id,
        was_repaired=was_repaired,
    )
