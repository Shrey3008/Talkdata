# TalkData

AI-powered natural language analytics platform. Ask a plain-English business question, get back auto-generated SQL, a results table, and an auto-selected chart — no SQL required.

## Stack

- **Frontend:** React (Vercel)
- **Backend:** FastAPI (Render)
- **Auth:** JWT with role-based access control (admin / member)
- **DB + vector store:** Supabase (Postgres + pgvector)
- **LLM:** Groq (natural language → SQL, schema-aware via pgvector RAG)
- **Pipeline:** Apache Airflow (local/dev dataset refresh)

## Status

- [x] Phase 1 — Backend scaffold, DB schema, JWT/RBAC auth
- [ ] Phase 2 — Schema-aware RAG (pgvector)
- [ ] Phase 3 — NL → SQL generation (Groq)
- [ ] Phase 4 — Frontend
- [ ] Phase 5 — Airflow pipeline
- [ ] Phase 6 — Integration
- [ ] Phase 7 — Deployment
- [ ] Phase 8 — Polish

## Backend setup

Requires Python 3.11+ and Docker (recommended) or a local venv.

1. Create a Supabase project, then in the SQL editor run:
   ```sql
   create extension if not exists vector;
   ```
   (The first Alembic migration also does this, but Supabase sometimes needs it enabled via the dashboard/SQL editor first depending on role permissions.)

2. Copy the env template and fill in your values:
   ```bash
   cd backend
   cp .env.example .env
   ```

3a. **Run with Docker (recommended):**
   ```bash
   docker compose up --build
   ```

3b. **Run locally without Docker:**
   ```bash
   cd backend
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   python seed.py
   uvicorn app.main:app --reload
   ```

4. Apply migrations and seed the sample manufacturing dataset (if not already done in step 3b):
   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python seed.py
   ```

5. Verify:
   ```bash
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/api/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","password":"password123"}'
   ```

API docs: http://localhost:8000/docs

## Sample dataset

Manufacturing ops data: `departments` → `machines` → `production_records` (units produced, downtime minutes, defect count, throughput rate) across 90 days x 3 shifts, seeded by `backend/seed.py`.
