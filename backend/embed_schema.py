"""(Re)build the schema_embeddings table from the curated schema docs.

Usage: python embed_schema.py
Safe to re-run: wipes and re-embeds all docs (they're small).
"""
import asyncio

from app.db.session import AsyncSessionLocal
from app.services.rag_service import reindex_schema


async def main() -> None:
    async with AsyncSessionLocal() as db:
        count = await reindex_schema(db)
    print(f"Embedded {count} schema docs into schema_embeddings.")


if __name__ == "__main__":
    asyncio.run(main())
