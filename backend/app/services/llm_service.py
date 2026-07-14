"""NL -> SQL generation via Groq."""
import re

from groq import AsyncGroq

from app.config import settings

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert PostgreSQL analyst for a manufacturing operations database.
Write a single read-only SQL query that answers the user's question.

Rules:
- PostgreSQL syntax only.
- Output ONLY the SQL query — no explanations, no markdown fences.
- One single SELECT statement (CTEs with WITH are allowed). Never modify data.
- Only use tables and columns from the provided schema context.
- Always give aggregate/computed columns clear snake_case aliases.
- When averaging or dividing integers, cast to numeric and ROUND to 2 decimals.
- Defect rate means SUM(defect_count)::numeric / NULLIF(SUM(units_produced), 0).
- Prefer human-readable columns (names over UUIDs) in the result.
- Order results in the way most useful for the question (e.g. largest first).
- If the question implies a time window, filter on record_date accordingly; CURRENT_DATE is available.
- Limit results to at most 100 rows unless the question requires otherwise."""

USER_TEMPLATE = """Schema context (the only tables/columns you may use):

{schema_context}

Question: {question}

SQL:"""

REPAIR_TEMPLATE = """The SQL you wrote failed. Fix it and output ONLY the corrected SQL.

Question: {question}

Schema context:
{schema_context}

Failed SQL:
{failed_sql}

Database error:
{error}

Corrected SQL:"""

_client: AsyncGroq | None = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client


def _strip_sql(text: str) -> str:
    """Remove markdown fences / leading 'sql' tokens the model sometimes adds."""
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return text.rstrip(";").strip()


async def generate_sql(question: str, schema_context: str) -> str:
    response = await get_client().chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(schema_context=schema_context, question=question)},
        ],
    )
    return _strip_sql(response.choices[0].message.content)


async def repair_sql(question: str, schema_context: str, failed_sql: str, error: str) -> str:
    response = await get_client().chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REPAIR_TEMPLATE.format(
                    question=question, schema_context=schema_context, failed_sql=failed_sql, error=error
                ),
            },
        ],
    )
    return _strip_sql(response.choices[0].message.content)
