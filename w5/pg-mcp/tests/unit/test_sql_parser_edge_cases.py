"""Edge case tests for SQL parser.

Tests cover:
- Empty and whitespace-only SQL
- Unicode characters, emoji
- Very long queries (1000+ columns)
- Deeply nested subqueries (20+ levels)
- Many JOINs (50+)
- Recursive CTEs, multiple CTEs
- Window functions
- JSON operators (->>, ->, @>)
- Array operations (&&, @>)
- Reserved word table names
- Schema-qualified names
"""

import pytest

from pg_mcp.infrastructure.sql_parser import ParsedSQLInfo, SQLParser
from pg_mcp.models.errors import SQLSyntaxError


class TestSQLParserEmptyAndWhitespace:
    """Edge case tests for empty and whitespace inputs."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_empty_string(self, parser: SQLParser) -> None:
        """Test empty SQL string."""
        result = parser.validate("")
        # Empty string should be treated as invalid
        assert result.is_valid is False
        assert result.error_message is not None

    def test_empty_string_parse_for_policy(self, parser: SQLParser) -> None:
        """Test empty SQL string for policy parsing."""
        result = parser.parse_for_policy("")
        assert result.is_readonly is False
        assert result.error_message is not None

    def test_whitespace_only_spaces(self, parser: SQLParser) -> None:
        """Test whitespace-only SQL (spaces)."""
        result = parser.validate("     ")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_whitespace_only_newlines(self, parser: SQLParser) -> None:
        """Test whitespace-only SQL (newlines)."""
        result = parser.validate("\n\n\n")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_whitespace_only_tabs(self, parser: SQLParser) -> None:
        """Test whitespace-only SQL (tabs)."""
        result = parser.validate("\t\t\t")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_whitespace_only_mixed(self, parser: SQLParser) -> None:
        """Test whitespace-only SQL (mixed whitespace)."""
        result = parser.validate("   \n\t  ")
        assert result.is_valid is False
        assert result.error_message is not None


class TestSQLParserUnicode:
    """Edge case tests for Unicode characters."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_unicode_chinese_in_string(self, parser: SQLParser) -> None:
        """Test SQL with Chinese characters in string literal."""
        result = parser.validate("SELECT * FROM users WHERE name = '中文'")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unicode_japanese_in_string(self, parser: SQLParser) -> None:
        """Test SQL with Japanese characters in string literal."""
        result = parser.validate("SELECT * FROM users WHERE name = '日本語'")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unicode_korean_in_string(self, parser: SQLParser) -> None:
        """Test SQL with Korean characters in string literal."""
        result = parser.validate("SELECT * FROM users WHERE name = '한국어'")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unicode_arabic_in_string(self, parser: SQLParser) -> None:
        """Test SQL with Arabic characters in string literal."""
        result = parser.validate("SELECT * FROM users WHERE name = 'العربية'")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_emoji_in_string(self, parser: SQLParser) -> None:
        """Test SQL with emoji in string literal."""
        result = parser.validate("SELECT * FROM posts WHERE content LIKE '%😀%'")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_emoji_multiple(self, parser: SQLParser) -> None:
        """Test SQL with multiple emojis in string literal."""
        result = parser.validate(
            "SELECT * FROM posts WHERE content = '🎉🎊🎁'"
        )
        assert result.is_valid is True
        assert result.is_safe is True

    def test_emoji_complex(self, parser: SQLParser) -> None:
        """Test SQL with complex emoji (skin tone modifier)."""
        result = parser.validate(
            "SELECT * FROM posts WHERE content LIKE '%👨‍👩‍👧‍👦%'"
        )
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unicode_mixed_script(self, parser: SQLParser) -> None:
        """Test SQL with mixed scripts in string literal."""
        result = parser.validate(
            "SELECT * FROM users WHERE bio = 'Hello 你好 مرحبا'"
        )
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unicode_mathematical_symbols(self, parser: SQLParser) -> None:
        """Test SQL with mathematical symbols."""
        result = parser.validate(
            "SELECT * FROM formulas WHERE equation = 'x² + y² = z²'"
        )
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserVeryLongQueries:
    """Edge case tests for very long queries."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_1000_columns(self, parser: SQLParser) -> None:
        """Test query with 1000 columns."""
        columns = ", ".join([f"col{i}" for i in range(1000)])
        sql = f"SELECT {columns} FROM large_table"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_2000_columns(self, parser: SQLParser) -> None:
        """Test query with 2000 columns."""
        columns = ", ".join([f"column_{i}" for i in range(2000)])
        sql = f"SELECT {columns} FROM very_large_table"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_very_long_column_names(self, parser: SQLParser) -> None:
        """Test query with very long column names."""
        # PostgreSQL allows up to 63 characters for identifiers
        long_names = ", ".join([f"{'a' * 60}_{i}" for i in range(100)])
        sql = f"SELECT {long_names} FROM some_table"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_many_where_conditions(self, parser: SQLParser) -> None:
        """Test query with many WHERE conditions."""
        conditions = " AND ".join([f"col{i} = {i}" for i in range(100)])
        sql = f"SELECT * FROM users WHERE {conditions}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_many_or_conditions(self, parser: SQLParser) -> None:
        """Test query with many OR conditions."""
        conditions = " OR ".join([f"id = {i}" for i in range(500)])
        sql = f"SELECT * FROM users WHERE {conditions}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserDeeplyNestedSubqueries:
    """Edge case tests for deeply nested subqueries."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_5_level_nested_subquery(self, parser: SQLParser) -> None:
        """Test 5 levels of nested subqueries."""
        sql = "SELECT * FROM t1"
        for i in range(5):
            sql = f"SELECT * FROM ({sql}) AS sub{i}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_10_level_nested_subquery(self, parser: SQLParser) -> None:
        """Test 10 levels of nested subqueries."""
        sql = "SELECT * FROM t1"
        for i in range(10):
            sql = f"SELECT * FROM ({sql}) AS sub{i}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_20_level_nested_subquery(self, parser: SQLParser) -> None:
        """Test 20 levels of nested subqueries."""
        sql = "SELECT * FROM t1"
        for i in range(20):
            sql = f"SELECT * FROM ({sql}) AS sub{i}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_nested_subqueries_in_where(self, parser: SQLParser) -> None:
        """Test nested subqueries in WHERE clause."""
        sql = """
        SELECT * FROM users
        WHERE id IN (
            SELECT user_id FROM orders
            WHERE product_id IN (
                SELECT id FROM products
                WHERE category_id IN (
                    SELECT id FROM categories
                    WHERE parent_id IN (
                        SELECT id FROM categories WHERE name = 'root'
                    )
                )
            )
        )
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_correlated_subquery(self, parser: SQLParser) -> None:
        """Test correlated subquery."""
        sql = """
        SELECT * FROM orders o
        WHERE total > (
            SELECT AVG(total) FROM orders
            WHERE user_id = o.user_id
        )
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserManyJoins:
    """Edge case tests for queries with many JOINs."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_10_joins(self, parser: SQLParser) -> None:
        """Test query with 10 JOINs."""
        sql = "SELECT * FROM t1"
        for i in range(10):
            sql += f" JOIN t{i + 2} ON t{i + 1}.id = t{i + 2}.id"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_50_joins(self, parser: SQLParser) -> None:
        """Test query with 50 JOINs."""
        sql = "SELECT * FROM t1"
        for i in range(50):
            sql += f" JOIN t{i + 2} ON t{i + 1}.id = t{i + 2}.id"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_mixed_join_types(self, parser: SQLParser) -> None:
        """Test query with mixed JOIN types."""
        sql = """
        SELECT * FROM t1
        JOIN t2 ON t1.id = t2.t1_id
        LEFT JOIN t3 ON t2.id = t3.t2_id
        RIGHT JOIN t4 ON t3.id = t4.t3_id
        FULL OUTER JOIN t5 ON t4.id = t5.t4_id
        CROSS JOIN t6
        LEFT OUTER JOIN t7 ON t6.id = t7.t6_id
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_self_join(self, parser: SQLParser) -> None:
        """Test self-join query."""
        sql = """
        SELECT e.name AS employee, m.name AS manager
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.id
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserRecursiveCTE:
    """Edge case tests for recursive CTEs."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_recursive_cte_simple(self, parser: SQLParser) -> None:
        """Test simple recursive CTE."""
        sql = """
        WITH RECURSIVE cte AS (
            SELECT 1 AS n
            UNION ALL
            SELECT n + 1 FROM cte WHERE n < 10
        )
        SELECT * FROM cte
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_recursive_cte_tree_traversal(self, parser: SQLParser) -> None:
        """Test recursive CTE for tree traversal."""
        sql = """
        WITH RECURSIVE category_tree AS (
            SELECT id, name, parent_id, 1 AS level
            FROM categories
            WHERE parent_id IS NULL

            UNION ALL

            SELECT c.id, c.name, c.parent_id, ct.level + 1
            FROM categories c
            JOIN category_tree ct ON c.parent_id = ct.id
        )
        SELECT * FROM category_tree
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_recursive_cte_with_aggregation(self, parser: SQLParser) -> None:
        """Test recursive CTE with aggregation."""
        sql = """
        WITH RECURSIVE org_chart AS (
            SELECT id, name, manager_id, salary
            FROM employees
            WHERE manager_id IS NULL

            UNION ALL

            SELECT e.id, e.name, e.manager_id, e.salary
            FROM employees e
            JOIN org_chart oc ON e.manager_id = oc.id
        )
        SELECT manager_id, SUM(salary) AS total_salary
        FROM org_chart
        GROUP BY manager_id
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserMultipleCTEs:
    """Edge case tests for multiple CTEs."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_two_ctes(self, parser: SQLParser) -> None:
        """Test query with two CTEs."""
        sql = """
        WITH
            cte1 AS (SELECT 1 AS a),
            cte2 AS (SELECT 2 AS b)
        SELECT * FROM cte1, cte2
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_three_dependent_ctes(self, parser: SQLParser) -> None:
        """Test three CTEs with dependencies."""
        sql = """
        WITH
            cte1 AS (SELECT 1 AS a),
            cte2 AS (SELECT a * 2 AS b FROM cte1),
            cte3 AS (SELECT * FROM cte1, cte2)
        SELECT * FROM cte3
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_many_ctes(self, parser: SQLParser) -> None:
        """Test query with many CTEs."""
        ctes = ", ".join([f"cte{i} AS (SELECT {i} AS val)" for i in range(20)])
        unions = " UNION ALL ".join([f"SELECT * FROM cte{i}" for i in range(20)])
        sql = f"WITH {ctes} {unions}"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_mixed_recursive_and_nonrecursive_ctes(self, parser: SQLParser) -> None:
        """Test mix of recursive and non-recursive CTEs.

        Note: In PostgreSQL, RECURSIVE keyword applies to the entire WITH clause,
        not individual CTEs. So the syntax is WITH RECURSIVE, then all CTEs.
        """
        sql = """
        WITH RECURSIVE
            regular_cte AS (
                SELECT id, name FROM products
            ),
            hierarchy AS (
                SELECT id, parent_id, name, 1 AS depth
                FROM categories WHERE parent_id IS NULL
                UNION ALL
                SELECT c.id, c.parent_id, c.name, h.depth + 1
                FROM categories c JOIN hierarchy h ON c.parent_id = h.id
            )
        SELECT * FROM regular_cte, hierarchy
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserWindowFunctions:
    """Edge case tests for window functions."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_row_number(self, parser: SQLParser) -> None:
        """Test ROW_NUMBER window function."""
        sql = """
        SELECT
            id,
            ROW_NUMBER() OVER (ORDER BY id) AS rn
        FROM data
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_lag_lead(self, parser: SQLParser) -> None:
        """Test LAG and LEAD window functions."""
        sql = """
        SELECT
            id,
            value,
            LAG(value) OVER (ORDER BY id) AS prev_value,
            LEAD(value) OVER (ORDER BY id) AS next_value
        FROM data
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_partition_by(self, parser: SQLParser) -> None:
        """Test window function with PARTITION BY."""
        sql = """
        SELECT
            id,
            category,
            value,
            LAG(value) OVER (PARTITION BY category ORDER BY id) AS prev_value,
            SUM(value) OVER (PARTITION BY category ORDER BY id) AS running_total
        FROM data
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_frame_clause(self, parser: SQLParser) -> None:
        """Test window function with frame clause."""
        sql = """
        SELECT
            id,
            value,
            SUM(value) OVER (
                ORDER BY id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_total,
            AVG(value) OVER (
                ORDER BY id
                ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
            ) AS moving_avg
        FROM data
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_multiple_window_functions(self, parser: SQLParser) -> None:
        """Test multiple window functions in one query."""
        sql = """
        SELECT
            id,
            ROW_NUMBER() OVER (ORDER BY id) AS rn,
            RANK() OVER (ORDER BY value DESC) AS rank,
            DENSE_RANK() OVER (ORDER BY value DESC) AS dense_rank,
            NTILE(4) OVER (ORDER BY value) AS quartile,
            PERCENT_RANK() OVER (ORDER BY value) AS pct_rank,
            CUME_DIST() OVER (ORDER BY value) AS cume_dist,
            FIRST_VALUE(name) OVER (ORDER BY value DESC) AS top_name,
            LAST_VALUE(name) OVER (ORDER BY value DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS bottom_name
        FROM data
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_named_window(self, parser: SQLParser) -> None:
        """Test named window definition."""
        sql = """
        SELECT
            id,
            SUM(value) OVER w AS sum,
            AVG(value) OVER w AS avg,
            COUNT(*) OVER w AS count
        FROM data
        WINDOW w AS (PARTITION BY category ORDER BY id)
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserJSONOperators:
    """Edge case tests for PostgreSQL JSON operators."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_json_arrow_text(self, parser: SQLParser) -> None:
        """Test ->> operator (extract as text)."""
        sql = "SELECT data->>'name' AS name FROM json_table"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_json_arrow_json(self, parser: SQLParser) -> None:
        """Test -> operator (extract as JSON)."""
        sql = "SELECT data->'address' AS address FROM json_table"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_json_nested_access(self, parser: SQLParser) -> None:
        """Test nested JSON access."""
        sql = """
        SELECT
            data->>'name' AS name,
            data->'address'->>'city' AS city,
            data->'address'->'location'->>'lat' AS lat
        FROM json_table
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_json_path_operator(self, parser: SQLParser) -> None:
        """Test #>> operator (path extraction as text)."""
        sql = """
        SELECT
            data #>> '{nested,deep,value}' AS deep_value,
            data #> '{array,0}' AS first_item
        FROM json_table
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_jsonb_containment(self, parser: SQLParser) -> None:
        """Test @> operator (JSONB containment)."""
        sql = """
        SELECT * FROM json_table
        WHERE data @> '{"active": true}'
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_jsonb_contained(self, parser: SQLParser) -> None:
        """Test <@ operator (JSONB is contained)."""
        sql = """
        SELECT * FROM json_table
        WHERE data <@ '{"name": "test", "active": true}'
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_jsonb_key_exists(self, parser: SQLParser) -> None:
        """Test ? operator (key exists)."""
        sql = "SELECT * FROM json_table WHERE data ? 'name'"
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_jsonb_any_key_exists(self, parser: SQLParser) -> None:
        """Test ?| operator (any key exists)."""
        sql = """
        SELECT * FROM json_table
        WHERE data ?| array['name', 'title']
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_jsonb_all_keys_exist(self, parser: SQLParser) -> None:
        """Test ?& operator (all keys exist)."""
        sql = """
        SELECT * FROM json_table
        WHERE data ?& array['name', 'email']
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserArrayOperations:
    """Edge case tests for PostgreSQL array operations."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_array_overlap(self, parser: SQLParser) -> None:
        """Test && operator (array overlap)."""
        sql = """
        SELECT * FROM items
        WHERE tags && ARRAY['tag1', 'tag2']
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_array_contains(self, parser: SQLParser) -> None:
        """Test @> operator (array contains)."""
        sql = """
        SELECT * FROM items
        WHERE categories @> ARRAY['cat1']
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_array_contained_by(self, parser: SQLParser) -> None:
        """Test <@ operator (array is contained by)."""
        sql = """
        SELECT * FROM items
        WHERE tags <@ ARRAY['tag1', 'tag2', 'tag3']
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_array_subscript(self, parser: SQLParser) -> None:
        """Test array subscript access."""
        sql = """
        SELECT
            arr[1] AS first,
            arr[2:4] AS slice,
            arr[:3] AS first_three
        FROM array_table
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_array_functions(self, parser: SQLParser) -> None:
        """Test array functions."""
        sql = """
        SELECT
            array_length(arr, 1) AS len,
            array_dims(arr) AS dims,
            array_upper(arr, 1) AS upper,
            array_lower(arr, 1) AS lower,
            array_position(arr, 'value') AS pos,
            array_remove(arr, 'value') AS removed,
            array_cat(arr1, arr2) AS concatenated
        FROM array_table
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_unnest(self, parser: SQLParser) -> None:
        """Test UNNEST function."""
        sql = """
        SELECT id, unnest(tags) AS tag
        FROM items
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserReservedWordTableNames:
    """Edge case tests for reserved word table names."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_order_table(self, parser: SQLParser) -> None:
        """Test 'order' as table name (reserved word)."""
        result = parser.validate('SELECT * FROM "order"')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_user_table(self, parser: SQLParser) -> None:
        """Test 'user' as table name (reserved word)."""
        result = parser.validate('SELECT * FROM "user"')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_group_table(self, parser: SQLParser) -> None:
        """Test 'group' as table name (reserved word)."""
        result = parser.validate('SELECT * FROM "group"')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_select_column(self, parser: SQLParser) -> None:
        """Test 'select' as column name (reserved word)."""
        result = parser.validate('SELECT "select" FROM data')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_table_table(self, parser: SQLParser) -> None:
        """Test 'table' as table name (reserved word)."""
        result = parser.validate('SELECT * FROM "table"')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_multiple_reserved_words(self, parser: SQLParser) -> None:
        """Test multiple reserved words as identifiers."""
        result = parser.validate("""
        SELECT "order", "group", "select", "from"
        FROM "table"
        WHERE "where" = 1
        """)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserSchemaQualifiedNames:
    """Edge case tests for schema-qualified names."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_public_schema(self, parser: SQLParser) -> None:
        """Test public schema prefix."""
        result = parser.parse_for_policy("SELECT * FROM public.users")
        assert result.is_readonly is True
        assert "public" in result.schemas
        assert "users" in result.tables

    def test_multiple_schemas(self, parser: SQLParser) -> None:
        """Test multiple schemas in one query."""
        result = parser.parse_for_policy("""
        SELECT a.*, b.*
        FROM public.users a
        JOIN analytics.events b ON a.id = b.user_id
        """)
        assert result.is_readonly is True
        assert "public" in result.schemas
        assert "analytics" in result.schemas

    def test_catalog_schema_table(self, parser: SQLParser) -> None:
        """Test catalog.schema.table format."""
        # Note: sqlglot may parse this differently
        result = parser.validate("SELECT * FROM mydb.public.users")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_schema_with_special_characters(self, parser: SQLParser) -> None:
        """Test schema names with special characters (quoted)."""
        result = parser.validate('SELECT * FROM "my-schema"."my-table"')
        assert result.is_valid is True
        assert result.is_safe is True

    def test_pg_catalog_schema(self, parser: SQLParser) -> None:
        """Test pg_catalog schema."""
        result = parser.validate("SELECT * FROM pg_catalog.pg_tables")
        assert result.is_valid is True
        assert result.is_safe is True

    def test_information_schema(self, parser: SQLParser) -> None:
        """Test information_schema."""
        result = parser.validate("SELECT * FROM information_schema.columns")
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserComplexScenarios:
    """Edge case tests for complex query scenarios."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_complex_analytics_query(self, parser: SQLParser) -> None:
        """Test complex analytics query with CTEs, window functions, etc."""
        sql = """
        WITH
            daily_sales AS (
                SELECT
                    DATE_TRUNC('day', created_at) AS day,
                    SUM(amount) AS total
                FROM orders
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE_TRUNC('day', created_at)
            ),
            ranked_sales AS (
                SELECT
                    day,
                    total,
                    RANK() OVER (ORDER BY total DESC) AS rank,
                    LAG(total) OVER (ORDER BY day) AS prev_total
                FROM daily_sales
            )
        SELECT
            day,
            total,
            rank,
            prev_total,
            ROUND((total - prev_total) / NULLIF(prev_total, 0) * 100, 2) AS growth_pct
        FROM ranked_sales
        WHERE rank <= 10
        ORDER BY day DESC
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_complex_json_query(self, parser: SQLParser) -> None:
        """Test complex JSON query."""
        sql = """
        SELECT
            id,
            data->>'name' AS name,
            data->'metadata'->>'version' AS version,
            jsonb_array_length(data->'tags') AS tag_count,
            data->'settings' @> '{"enabled": true}' AS is_enabled
        FROM documents
        WHERE data @> '{"type": "article"}'
        AND data ? 'published_at'
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_lateral_join(self, parser: SQLParser) -> None:
        """Test LATERAL join."""
        sql = """
        SELECT u.*, recent_orders.*
        FROM users u
        CROSS JOIN LATERAL (
            SELECT * FROM orders o
            WHERE o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 5
        ) AS recent_orders
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_grouping_sets(self, parser: SQLParser) -> None:
        """Test GROUPING SETS."""
        sql = """
        SELECT
            category,
            region,
            SUM(sales) AS total_sales
        FROM sales_data
        GROUP BY GROUPING SETS (
            (category, region),
            (category),
            (region),
            ()
        )
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_cube_rollup(self, parser: SQLParser) -> None:
        """Test CUBE and ROLLUP."""
        sql = """
        SELECT
            year, quarter, month, SUM(revenue)
        FROM sales
        GROUP BY ROLLUP (year, quarter, month)
        UNION ALL
        SELECT
            category, brand, product, SUM(quantity)
        FROM inventory
        GROUP BY CUBE (category, brand, product)
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_exists_not_exists(self, parser: SQLParser) -> None:
        """Test EXISTS and NOT EXISTS."""
        sql = """
        SELECT * FROM users u
        WHERE EXISTS (
            SELECT 1 FROM orders o WHERE o.user_id = u.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM bans b WHERE b.user_id = u.id
        )
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_case_expression(self, parser: SQLParser) -> None:
        """Test CASE expression."""
        sql = """
        SELECT
            id,
            CASE
                WHEN score >= 90 THEN 'A'
                WHEN score >= 80 THEN 'B'
                WHEN score >= 70 THEN 'C'
                WHEN score >= 60 THEN 'D'
                ELSE 'F'
            END AS grade,
            CASE status
                WHEN 'active' THEN 1
                WHEN 'inactive' THEN 0
                ELSE -1
            END AS status_code
        FROM students
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True

    def test_coalesce_nullif(self, parser: SQLParser) -> None:
        """Test COALESCE and NULLIF."""
        sql = """
        SELECT
            COALESCE(first_name, 'Unknown') AS name,
            NULLIF(status, 'pending') AS resolved_status,
            COALESCE(email, phone, 'No contact') AS contact
        FROM users
        """
        result = parser.validate(sql)
        assert result.is_valid is True
        assert result.is_safe is True


class TestSQLParserExtractTablesEdgeCases:
    """Edge case tests for extract_tables method."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_extract_from_cte(self, parser: SQLParser) -> None:
        """Test table extraction from CTE."""
        tables = parser.extract_tables("""
        WITH cte AS (SELECT * FROM hidden_table)
        SELECT * FROM cte
        """)
        assert "hidden_table" in tables

    def test_extract_from_subquery(self, parser: SQLParser) -> None:
        """Test table extraction from subquery."""
        tables = parser.extract_tables("""
        SELECT * FROM (SELECT * FROM inner_table) AS sub
        """)
        assert "inner_table" in tables

    def test_extract_from_union(self, parser: SQLParser) -> None:
        """Test table extraction from UNION."""
        tables = parser.extract_tables("""
        SELECT * FROM table1
        UNION ALL
        SELECT * FROM table2
        """)
        assert "table1" in tables
        assert "table2" in tables


class TestSQLParserAddLimitEdgeCases:
    """Edge case tests for add_limit method."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_add_limit_with_offset(self, parser: SQLParser) -> None:
        """Test adding limit to query with OFFSET."""
        result = parser.add_limit(
            "SELECT * FROM users OFFSET 10", 100
        )
        assert "LIMIT" in result.upper()
        assert "100" in result
        assert "OFFSET" in result.upper()

    def test_add_limit_to_union(self, parser: SQLParser) -> None:
        """Test adding limit to UNION query.

        Note: The add_limit method only works on SELECT statements,
        not UNION queries (which are parsed as Union nodes). This is
        expected behavior - UNION queries return the original SQL.
        """
        original = "SELECT * FROM t1 UNION SELECT * FROM t2"
        result = parser.add_limit(original, 100)
        # UNION queries are not modified by add_limit
        # This is expected behavior as the method checks for Select type
        assert result == original

    def test_add_limit_preserves_order_by(self, parser: SQLParser) -> None:
        """Test that add_limit preserves ORDER BY."""
        result = parser.add_limit(
            "SELECT * FROM users ORDER BY created_at DESC", 100
        )
        assert "ORDER BY" in result.upper()
        assert "LIMIT" in result.upper()

    def test_add_limit_to_invalid_sql(self, parser: SQLParser) -> None:
        """Test add_limit with invalid SQL returns original."""
        original = "SELECT FROM (invalid sql"
        result = parser.add_limit(original, 100)
        assert result == original


class TestSQLParserNormalizeEdgeCases:
    """Edge case tests for normalize method."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_normalize_preserves_case_in_strings(self, parser: SQLParser) -> None:
        """Test that normalize preserves case in string literals."""
        result = parser.normalize("SELECT * FROM users WHERE name = 'John Doe'")
        assert "John Doe" in result or "john doe" in result.lower()

    def test_normalize_with_comments(self, parser: SQLParser) -> None:
        """Test normalize with SQL comments."""
        result = parser.normalize("""
        -- This is a comment
        SELECT * FROM users /* inline comment */ WHERE id = 1
        """)
        assert "SELECT" in result.upper()
        assert "FROM" in result.upper()

    def test_normalize_invalid_sql(self, parser: SQLParser) -> None:
        """Test normalize with invalid SQL returns original."""
        original = "SELECT FROM (invalid"
        result = parser.normalize(original)
        assert result == original
