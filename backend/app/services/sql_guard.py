"""Validation layer for LLM-generated SQL.

Defense in depth: this parser-based whitelist check is the first gate; the
executor additionally runs inside a READ ONLY transaction with a statement
timeout, so even a query that slips past validation cannot write or hang.
"""
import sqlglot
from sqlglot import exp

# The only tables NL-generated SQL may touch (sample dataset only — never app tables).
ALLOWED_TABLES = {"departments", "machines", "production_records"}

MAX_ROWS = 500


class SQLValidationError(Exception):
    pass


def validate_sql(sql: str) -> str:
    """Parse, check, and return the SQL (with a row cap applied). Raises on violation."""
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise SQLValidationError(f"SQL failed to parse: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed")

    tree = statements[0]

    root = tree
    if isinstance(root, exp.With):
        root = root.this
    if not isinstance(root, exp.Select) and not (
        isinstance(tree, exp.Select) or tree.find(exp.Select)
    ):
        raise SQLValidationError("Only SELECT statements are allowed")
    if not isinstance(tree, (exp.Select, exp.With, exp.Union)):
        raise SQLValidationError("Only SELECT statements are allowed")

    forbidden = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
        exp.TruncateTable, exp.Grant, exp.Command, exp.Merge, exp.Set,
    )
    for node_type in forbidden:
        if tree.find(node_type):
            raise SQLValidationError("Only read-only SELECT statements are allowed")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name in cte_names:
            continue
        if table.db or table.catalog:
            raise SQLValidationError(f"Schema-qualified table not allowed: {table.sql()}")
        if name not in ALLOWED_TABLES:
            raise SQLValidationError(f"Table not allowed: {name}")

    # Block function calls that read files / execute / touch system state.
    for func in tree.find_all(exp.Anonymous):
        fname = (func.this or "").lower() if isinstance(func.this, str) else ""
        if fname.startswith(("pg_", "current_setting", "set_config", "dblink", "lo_")):
            raise SQLValidationError(f"Function not allowed: {fname}")

    # Enforce a row cap: wrap or clamp LIMIT.
    limit = tree.args.get("limit")
    if isinstance(tree, (exp.Select, exp.With)) and limit is None:
        tree = tree.limit(MAX_ROWS)
    elif limit is not None:
        try:
            if int(limit.expression.this) > MAX_ROWS:
                tree = tree.limit(MAX_ROWS)
        except (TypeError, ValueError, AttributeError):
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="postgres")
