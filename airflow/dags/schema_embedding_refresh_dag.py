"""Weekly refresh of the schema_embeddings pgvector table.

The curated schema docs live in the backend codebase
(backend/app/services/schema_metadata.py, mounted read-only at
/opt/shared/schema_metadata.py) so Airflow and the API embed the exact same
source of truth.

  extract_docs -> embed_and_load -> validate_retrieval
"""
from __future__ import annotations

import logging
import os
import sys

import pendulum
from airflow.decorators import dag, task

log = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def _engine():
    from sqlalchemy import create_engine

    url = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    return create_engine(url, pool_pre_ping=True)


@dag(
    dag_id="schema_embedding_refresh",
    description="Re-embed curated schema metadata into pgvector for the NL->SQL RAG layer",
    schedule="0 4 * * 0",  # 04:00 UTC Sundays
    start_date=pendulum.datetime(2026, 7, 1, tz="UTC"),
    catchup=False,
    default_args={"retries": 1, "retry_delay": pendulum.duration(minutes=5)},
    tags=["talkdata", "rag"],
)
def schema_embedding_refresh():
    @task
    def extract_docs() -> list[dict]:
        """Load the curated table/column docs shared with the backend."""
        sys.path.insert(0, "/opt/shared")
        from schema_metadata import SCHEMA_DOCS  # noqa: PLC0415

        docs = [
            {"table_name": d.table_name, "column_name": d.column_name, "content": d.content}
            for d in SCHEMA_DOCS
        ]
        log.info("Extracted %d schema docs", len(docs))
        assert docs, "schema metadata is empty"
        return docs

    @task
    def embed_and_load(docs: list[dict]) -> int:
        """Embed all docs and atomically replace the schema_embeddings table."""
        from fastembed import TextEmbedding
        from sqlalchemy import text

        model = TextEmbedding(model_name=EMBEDDING_MODEL)
        vectors = [v.tolist() for v in model.embed([d["content"] for d in docs])]
        assert all(len(v) == EMBEDDING_DIM for v in vectors), "unexpected embedding dimension"

        with _engine().begin() as conn:  # delete + insert in one txn: readers never see empty
            conn.execute(text("delete from schema_embeddings"))
            for doc, vector in zip(docs, vectors):
                conn.execute(
                    text("""
                        insert into schema_embeddings
                          (id, table_name, column_name, content, embedding)
                        values
                          (gen_random_uuid(), :table_name, :column_name, :content,
                           (:embedding)::vector)
                    """),
                    {**doc, "embedding": str(vector)},
                )
        log.info("Loaded %d embeddings", len(vectors))
        return len(vectors)

    @task
    def validate_retrieval(loaded: int) -> None:
        """Smoke-test retrieval: a downtime question must rank downtime docs first."""
        from fastembed import TextEmbedding
        from sqlalchemy import text

        model = TextEmbedding(model_name=EMBEDDING_MODEL)
        probe = list(model.embed(["which department has the most downtime?"]))[0].tolist()

        with _engine().connect() as conn:
            count = conn.execute(text("select count(*) from schema_embeddings")).scalar()
            top = conn.execute(
                text("""
                    select table_name, coalesce(column_name, '(table)') as col
                    from schema_embeddings
                    order by embedding <=> (:probe)::vector
                    limit 3
                """),
                {"probe": str(probe)},
            ).mappings().all()

        assert count == loaded, f"expected {loaded} embeddings, found {count}"
        top_names = [f"{r['table_name']}.{r['col']}" for r in top]
        log.info("Probe retrieval top-3: %s", top_names)
        assert any("downtime" in n or "departments" in n for n in top_names), (
            f"retrieval sanity check failed, top-3 was {top_names}"
        )

    validate_retrieval(embed_and_load(extract_docs()))


schema_embedding_refresh()
