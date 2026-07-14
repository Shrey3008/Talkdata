# TalkData — Project Log

Running record of what was built in each phase, why key decisions were made, what broke, and what's verified vs. pending. Updated at the end of every phase.

---

## Phase 0 — Planning & Setup

### What was built
No code — project scoping, stack selection, and account setup. TalkData is an AI-powered natural-language analytics platform: users type plain-English business questions and get back auto-generated SQL, a results table, and an auto-selected chart. Built as a portfolio project on free-tier services only (no AWS).

Accounts provisioned: Groq (LLM API), Supabase (Postgres + pgvector), Render (backend hosting), Vercel (frontend hosting). Local tooling: Docker Desktop (installed during Phase 1 verification).

### Key decisions
- **FastAPI over Node/Express for the backend.** Airflow DAGs are Python-only, so a Python backend lets the API and the data pipeline share DB models, schema-metadata extraction, and embedding logic instead of duplicating them across two languages. The RAG pipeline and data cleaning also lean on the Python data ecosystem (pandas, SQLAlchemy). FastAPI + Pydantic adds free request validation and auto-generated OpenAPI docs. Node's usual advantage (same language as the React frontend) doesn't apply since the backend deploys separately to Render and talks to the frontend over REST either way.
- **Supabase for both the app database and the vector store.** One free-tier Postgres instance covers relational data and embeddings via the pgvector extension — no separate vector DB to provision, and schema metadata lives next to the schema it describes.
- **Airflow local-only + lightweight scheduler in production.** Airflow's normal footprint (webserver + scheduler + worker + metadata DB, all long-running) doesn't fit Render's free tier, which spins services down on inactivity. Decision: run full Airflow via docker-compose locally for development/demo (real DAG code in the repo, demo clip for the portfolio), and use a Render Cron Job or APScheduler for the deployed app's periodic dataset refresh. Keeps the live app functional while still demonstrating Airflow skills.
- **Project lives in its own repo** (`~/Desktop/talkdata`), separate from the personal portfolio site repo.

### Bugs / issues
None (no code yet).

### Status
- ✅ Stack finalized, build plan approved
- ✅ All accounts created

---

## Phase 1 — Backend scaffold, DB schema, JWT/RBAC auth, sample dataset

### What was built
The FastAPI backend skeleton with a working auth system and a realistic manufacturing sample dataset, all running in Docker against the hosted Supabase database.

- **Database schema** (via a single Alembic migration):
  - `users` — email/password accounts with an `admin`/`member` role enum for RBAC
  - `departments` → `machines` → `production_records` — the manufacturing sample data (units produced, downtime minutes, defect count, throughput rate, per machine per shift per day)
  - `query_history` — every NL question a user asks plus the SQL generated for it
  - `pinned_queries` — saved queries that will power the mini-dashboard feature
  - `schema_embeddings` — pgvector table holding embedded table/column metadata (populated in Phase 2)
  - The migration also enables the `vector` Postgres extension
- **Auth**: signup, login, token refresh, and `/me` endpoints. JWT access tokens (30 min) + refresh tokens (7 days), bcrypt password hashing, and a `require_role()` FastAPI dependency for role-gated endpoints.
- **Seed script** (`backend/seed.py`): generates 90 days × 3 shifts of production data across 5 departments and 24 machines (~6,500 records) with per-machine baseline throughput/defect rates plus gaussian noise, so aggregate queries return realistic-looking results. Idempotent — skips if data exists.
- **Dev environment**: backend Dockerfile (Python 3.11-slim) + root docker-compose with hot reload.

### Key decisions
- **Async SQLAlchemy 2.0 + asyncpg** rather than sync: FastAPI is async-native, and the query endpoint (Phase 3) will hold connections open while waiting on Groq, where async pays off.
- **Embedding dimension fixed at 384** in the `schema_embeddings` table, matching the all-MiniLM-L6-v2 sentence-transformer model planned for Phase 2 RAG (small, free, runs locally).
- **No ANN index (ivfflat/hnsw) on the embeddings column.** Schema metadata will be dozens of rows, not millions — a sequential scan is faster at that scale and avoids ivfflat's staleness problem (the index is trained on whatever data exists at creation time).
- **JWT payload carries the role claim**, but RBAC checks re-fetch the user from the DB on each request, so deactivating a user or changing their role takes effect immediately rather than when the token expires.

### Bugs / issues hit
1. **Supabase direct DB host is IPv6-only; local network has no IPv6 route.** `db.<ref>.supabase.co` resolves to only an AAAA record, and the machine had no IPv6 connectivity, so nothing could connect. Fix: connect through Supabase's IPv4 session pooler (`aws-0-ca-central-1.pooler.supabase.com:5432`, username `postgres.<project-ref>`). Same approach will be used on Render.
2. **Alembic migration created the `user_role` enum twice.** The migration created the enum explicitly, then `create_table` tried to create it again via the column type → `DuplicateObjectError`. Fix: `create_type=False` on the column's `postgresql.ENUM`.
3. **passlib 1.7.4 crashes with modern bcrypt.** passlib is unmaintained and breaks against bcrypt ≥ 4.1 (`module 'bcrypt' has no attribute '__about__'`, plus a spurious 72-byte password error), causing 500s on signup. Fix: dropped passlib entirely and call `bcrypt` directly for hashing/verification.
4. **Local machine constraint (noted, not a code bug):** macOS ships Python 3.9.6, which can't run the SQLAlchemy 2.0-style `str | None` annotations (needs 3.10+). Everything runs in Docker (Python 3.11), so this only matters for running the backend outside Docker.

### Status
- ✅ Migration applied to Supabase; all tables + pgvector extension live
- ✅ Sample data seeded: 5 departments, 24 machines, 6,480 production records
- ✅ Signup / login / `/me` verified end-to-end (valid tokens accepted, invalid rejected)
- ✅ Aggregate SQL over seeded data returns sensible per-department numbers
- ✅ Committed to git (`.env` excluded)
- ⏳ RBAC admin-only endpoint not yet exercised (no admin-only routes exist yet — first one arrives with the admin refresh endpoint in a later phase)
- ⏳ Automated tests deferred to Phase 8 (polish)

---

## Phase 2 — Schema-aware RAG (pgvector) — *not started*

## Phase 3 — NL → SQL generation (Groq) — *not started*

## Phase 4 — Frontend (React) — *not started*

## Phase 5 — Airflow pipeline — *not started*

## Phase 6 — Integration — *not started*

## Phase 7 — Deployment (Render + Vercel) — *not started*

## Phase 8 — Polish — *not started*
