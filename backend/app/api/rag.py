from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.rag import RagDocOut, RagSearchRequest, RagSearchResponse
from app.services.rag_service import format_context_for_prompt, reindex_schema, retrieve_schema_context

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
async def search_schema(
    payload: RagSearchRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
) -> RagSearchResponse:
    """Debug/inspection endpoint: see which schema docs a question retrieves."""
    docs = await retrieve_schema_context(db, payload.question, payload.top_k)
    return RagSearchResponse(
        question=payload.question,
        results=[RagDocOut(**doc.__dict__) for doc in docs],
        prompt_context=format_context_for_prompt(docs),
    )


@router.post("/reindex")
async def reindex(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
) -> dict[str, int]:
    """Re-embed the curated schema docs (after schema/metadata changes)."""
    count = await reindex_schema(db)
    return {"embedded_docs": count}
