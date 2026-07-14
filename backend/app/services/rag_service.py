"""Schema-aware retrieval: embed the curated schema docs into pgvector, and for
an incoming question return the most relevant tables/columns as prompt context.
"""
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema_embedding import SchemaEmbedding
from app.services.embedding_service import embed_query, embed_texts
from app.services.schema_metadata import SCHEMA_DOCS

DEFAULT_TOP_K = 8


async def reindex_schema(db: AsyncSession) -> int:
    """Replace all schema embeddings with freshly embedded curated docs."""
    vectors = embed_texts([doc.content for doc in SCHEMA_DOCS])

    await db.execute(delete(SchemaEmbedding))
    db.add_all(
        SchemaEmbedding(
            table_name=doc.table_name,
            column_name=doc.column_name,
            content=doc.content,
            embedding=vector,
        )
        for doc, vector in zip(SCHEMA_DOCS, vectors)
    )
    await db.commit()
    return len(SCHEMA_DOCS)


@dataclass
class RetrievedDoc:
    table_name: str
    column_name: str | None
    content: str
    similarity: float


async def retrieve_schema_context(
    db: AsyncSession, question: str, top_k: int = DEFAULT_TOP_K
) -> list[RetrievedDoc]:
    """Return the top_k schema docs most similar to the question (cosine)."""
    query_vector = embed_query(question)
    distance = SchemaEmbedding.embedding.cosine_distance(query_vector)

    rows = (
        await db.execute(
            select(SchemaEmbedding, distance.label("distance")).order_by(distance).limit(top_k)
        )
    ).all()

    return [
        RetrievedDoc(
            table_name=row.SchemaEmbedding.table_name,
            column_name=row.SchemaEmbedding.column_name,
            content=row.SchemaEmbedding.content,
            similarity=round(1.0 - row.distance, 4),
        )
        for row in rows
    ]


def format_context_for_prompt(docs: list[RetrievedDoc]) -> str:
    """Assemble retrieved docs into the schema-context block for the LLM prompt.

    Table-level docs come first (they carry join info), then column docs,
    de-duplicated and grouped per table for readability.
    """
    tables = sorted({d.table_name for d in docs})
    lines: list[str] = []
    for table in tables:
        table_docs = [d for d in docs if d.table_name == table]
        table_docs.sort(key=lambda d: (d.column_name is not None, d.column_name or ""))
        lines.extend(d.content for d in table_docs)
        lines.append("")
    return "\n".join(lines).strip()
