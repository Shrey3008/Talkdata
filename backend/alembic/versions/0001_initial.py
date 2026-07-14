"""initial schema: users, manufacturing sample data, query history, pinned queries, schema embeddings

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    user_role = postgresql.ENUM("admin", "member", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )

    op.create_table(
        "machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("machine_type", sa.String(100), nullable=False),
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("departments.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "production_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "machine_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("machines.id"), nullable=False
        ),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("shift", sa.String(20), nullable=False),
        sa.Column("units_produced", sa.Integer, nullable=False),
        sa.Column("downtime_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("defect_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("throughput_rate", sa.Float, nullable=False),
    )
    op.create_index("ix_production_records_machine_id", "production_records", ["machine_id"])
    op.create_index("ix_production_records_record_date", "production_records", ["record_date"])

    op.create_table(
        "query_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("generated_sql", sa.Text, nullable=False),
        sa.Column("chart_type", sa.String(20), nullable=True),
        sa.Column("result_row_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_query_history_user_id", "query_history", ["user_id"])

    op.create_table(
        "pinned_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("generated_sql", sa.Text, nullable=False),
        sa.Column("chart_type", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pinned_queries_user_id", "pinned_queries", ["user_id"])

    op.create_table(
        "schema_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("column_name", sa.String(100), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_schema_embeddings_table_name", "schema_embeddings", ["table_name"])
    # No ANN index (ivfflat/hnsw) on embedding: schema metadata is expected to stay in the
    # dozens-to-low-hundreds of rows, where a sequential scan outperforms an approximate index
    # and avoids ivfflat's "trained on whatever data existed at CREATE INDEX time" staleness issue.


def downgrade() -> None:
    op.drop_table("schema_embeddings")
    op.drop_table("pinned_queries")
    op.drop_table("query_history")
    op.drop_table("production_records")
    op.drop_table("machines")
    op.drop_table("departments")
    op.drop_table("users")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
