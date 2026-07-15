"""The SQL guard is the security boundary between LLM output and the database —
every category of attack it must stop gets a test.
"""
import pytest

from app.services.sql_guard import MAX_ROWS, SQLValidationError, validate_sql


class TestAllowsLegitimateQueries:
    def test_simple_select(self):
        out = validate_sql("SELECT name FROM departments")
        assert "SELECT" in out and "departments" in out

    def test_join_across_whitelisted_tables(self):
        out = validate_sql(
            "SELECT d.name, SUM(pr.units_produced) FROM production_records pr "
            "JOIN machines m ON pr.machine_id = m.id "
            "JOIN departments d ON m.department_id = d.id GROUP BY d.name"
        )
        assert "JOIN" in out

    def test_cte(self):
        out = validate_sql(
            "WITH totals AS (SELECT machine_id, SUM(units_produced) AS u "
            "FROM production_records GROUP BY machine_id) "
            "SELECT * FROM totals ORDER BY u DESC"
        )
        assert "WITH" in out

    def test_aggregates_and_case(self):
        out = validate_sql(
            "SELECT shift, ROUND(AVG(throughput_rate)::numeric, 2), "
            "CASE WHEN SUM(defect_count) > 100 THEN 'high' ELSE 'low' END "
            "FROM production_records GROUP BY shift"
        )
        assert "CASE" in out


class TestBlocksWrites:
    @pytest.mark.parametrize(
        "sql",
        [
            "DELETE FROM users",
            "DROP TABLE production_records",
            "UPDATE users SET role = 'admin'",
            "INSERT INTO users (email) VALUES ('x@x.com')",
            "TRUNCATE production_records",
            "CREATE TABLE evil (id int)",
            "ALTER TABLE users ADD COLUMN pwned int",
            "GRANT ALL ON users TO PUBLIC",
        ],
    )
    def test_write_statement_rejected(self, sql):
        with pytest.raises(SQLValidationError):
            validate_sql(sql)

    def test_multi_statement_rejected(self):
        with pytest.raises(SQLValidationError, match="one SQL statement"):
            validate_sql("SELECT 1; DROP TABLE users")

    def test_select_into_rejected(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT * INTO evil FROM departments")


class TestBlocksTableEscapes:
    def test_non_whitelisted_table(self):
        with pytest.raises(SQLValidationError, match="Table not allowed: users"):
            validate_sql("SELECT email, hashed_password FROM users")

    def test_app_tables_hidden(self):
        for table in ("query_history", "pinned_queries", "schema_embeddings"):
            with pytest.raises(SQLValidationError, match="Table not allowed"):
                validate_sql(f"SELECT * FROM {table}")

    def test_schema_qualified_rejected(self):
        with pytest.raises(SQLValidationError, match="Schema-qualified"):
            validate_sql("SELECT * FROM public.users")

    def test_pg_catalog_rejected(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT * FROM pg_catalog.pg_tables")

    def test_information_schema_rejected(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT table_name FROM information_schema.tables")

    def test_sneaky_join_to_users(self):
        with pytest.raises(SQLValidationError, match="users"):
            validate_sql(
                "SELECT d.name, u.email FROM departments d JOIN users u ON true"
            )

    def test_subquery_against_users(self):
        with pytest.raises(SQLValidationError, match="users"):
            validate_sql(
                "SELECT name FROM departments WHERE id IN (SELECT id FROM users)"
            )

    def test_cte_name_cannot_shadow_forbidden_table_then_use_real_one(self):
        # CTE named 'users' is fine as an alias, but the real users table inside is not.
        with pytest.raises(SQLValidationError):
            validate_sql("WITH users AS (SELECT * FROM users) SELECT * FROM users")

    def test_cte_alias_is_allowed_as_reference(self):
        out = validate_sql(
            "WITH top_m AS (SELECT machine_id FROM production_records LIMIT 5) "
            "SELECT * FROM top_m"
        )
        assert "top_m" in out


class TestBlocksDangerousFunctions:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT pg_read_file('/etc/passwd')",
            "SELECT pg_sleep(60)",
            "SELECT current_setting('data_directory')",
            "SELECT set_config('x', 'y', false)",
        ],
    )
    def test_system_function_rejected(self, sql):
        with pytest.raises(SQLValidationError):
            validate_sql(sql)


class TestRowCap:
    def test_missing_limit_gets_capped(self):
        out = validate_sql("SELECT name FROM departments")
        assert f"LIMIT {MAX_ROWS}" in out

    def test_oversized_limit_clamped(self):
        out = validate_sql("SELECT name FROM departments LIMIT 999999")
        assert f"LIMIT {MAX_ROWS}" in out

    def test_small_limit_preserved(self):
        out = validate_sql("SELECT name FROM departments LIMIT 5")
        assert "LIMIT 5" in out


class TestMalformedInput:
    def test_empty(self):
        with pytest.raises(SQLValidationError):
            validate_sql("")

    def test_not_sql(self):
        with pytest.raises(SQLValidationError):
            validate_sql("I'm sorry, I cannot answer that question.")

    def test_explain_rejected(self):
        with pytest.raises(SQLValidationError):
            validate_sql("EXPLAIN ANALYZE SELECT * FROM departments")
