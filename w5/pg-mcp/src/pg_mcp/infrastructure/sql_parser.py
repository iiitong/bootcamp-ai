import re

import sqlglot
from sqlglot import exp

from pg_mcp.models.errors import SQLSyntaxError, UnsafeSQLError
from pg_mcp.models.query import SQLValidationResult

# 禁止的语句类型
FORBIDDEN_STATEMENT_TYPES: set[type[exp.Expression]] = {
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Revoke,  # 权限撤销
    exp.Command,
    exp.Set,  # SET ROLE 等
}

# 禁止的危险函数
FORBIDDEN_FUNCTIONS: set[str] = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_reload_conf",
    "pg_rotate_logfile",
    "lo_import",
    "lo_export",
    "lo_unlink",
    "dblink",
    "dblink_exec",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_write_file",
    "pg_ls_dir",
}

# 禁止的关键字（正则匹配）
FORBIDDEN_KEYWORDS_PATTERNS: list[tuple[str, str]] = [
    # 文件操作
    (r"\bCOPY\s+.*\s+TO\b", "COPY TO"),
    (r"\bCOPY\s+.*\s+FROM\b", "COPY FROM"),
    # SELECT 变体
    (r"\bSELECT\s+.*\s+INTO\s+(?!@)", "SELECT INTO"),  # 排除变量赋值
    (r"\bFOR\s+UPDATE\b", "FOR UPDATE"),
    (r"\bFOR\s+SHARE\b", "FOR SHARE"),
    (r"\bFOR\s+NO\s+KEY\s+UPDATE\b", "FOR NO KEY UPDATE"),
    (r"\bFOR\s+KEY\s+SHARE\b", "FOR KEY SHARE"),
    # 会话/角色操作
    (r"\bSET\s+ROLE\b", "SET ROLE"),
    (r"\bSET\s+SESSION\s+AUTHORIZATION\b", "SET SESSION AUTHORIZATION"),
    (r"\bRESET\s+ROLE\b", "RESET ROLE"),
    # 其他危险操作
    (r"\bLISTEN\b", "LISTEN"),
    (r"\bNOTIFY\b", "NOTIFY"),
    (r"\bUNLISTEN\b", "UNLISTEN"),
]


class SQLParser:
    """SQL 解析与验证器"""

    def __init__(self, dialect: str = "postgres") -> None:
        """初始化解析器

        Args:
            dialect: SQL 方言
        """
        self.dialect = dialect
        # 预编译正则表达式
        self._keyword_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in FORBIDDEN_KEYWORDS_PATTERNS
        ]

    def parse(self, sql: str) -> list[exp.Expression]:
        """解析 SQL 语句

        Args:
            sql: SQL 语句

        Returns:
            解析后的语句列表

        Raises:
            SQLSyntaxError: SQL 语法错误
        """
        try:
            statements = sqlglot.parse(sql, dialect=self.dialect)
            # 过滤掉 None 值（可能由于空语句产生）
            return [stmt for stmt in statements if stmt is not None]
        except sqlglot.errors.ParseError as e:
            raise SQLSyntaxError(sql, str(e)) from e

    def validate(self, sql: str) -> SQLValidationResult:
        """验证 SQL 安全性

        Args:
            sql: SQL 语句

        Returns:
            验证结果
        """
        warnings: list[str] = []

        # 1. 先做关键字检查（文本级别）
        keyword_error = self._check_forbidden_keywords(sql)
        if keyword_error:
            return SQLValidationResult(
                is_valid=True,  # 语法可能正确
                is_safe=False,
                error_message=keyword_error,
            )

        # 2. 解析 SQL
        try:
            statements = self.parse(sql)
        except SQLSyntaxError as e:
            return SQLValidationResult(
                is_valid=False,
                is_safe=False,
                error_message=e.message,
            )

        # 3. 检查多语句（stacked queries）
        if len(statements) > 1:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message="Multiple statements (stacked queries) are not allowed",
            )

        if not statements:
            return SQLValidationResult(
                is_valid=False,
                is_safe=False,
                error_message="No valid SQL statement found",
            )

        stmt = statements[0]

        # 4. 检查语句类型
        type_error = self._check_statement_type(stmt)
        if type_error:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message=type_error,
            )

        # 5. 检查危险函数
        func_error = self._check_dangerous_functions(stmt)
        if func_error:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message=func_error,
            )

        # 6. 检查 SELECT 变体（INTO, FOR UPDATE 等）
        variant_error = self._check_select_variants(stmt)
        if variant_error:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message=variant_error,
            )

        # 7. 检查子查询和 CTE 中的修改操作
        subquery_error = self._check_subqueries(stmt)
        if subquery_error:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message=subquery_error,
            )

        return SQLValidationResult(
            is_valid=True,
            is_safe=True,
            warnings=warnings,
        )

    def _check_forbidden_keywords(self, sql: str) -> str | None:
        """检查禁止的关键字

        Args:
            sql: SQL 语句

        Returns:
            错误消息或 None
        """
        for pattern, name in self._keyword_patterns:
            if pattern.search(sql):
                return f"Forbidden keyword detected: {name}"
        return None

    def _check_statement_type(self, stmt: exp.Expression) -> str | None:
        """检查语句类型是否允许

        Args:
            stmt: 解析后的语句

        Returns:
            错误消息或 None
        """
        for forbidden_type in FORBIDDEN_STATEMENT_TYPES:
            if isinstance(stmt, forbidden_type):
                return f"Statement type '{stmt.key}' is not allowed (read-only queries only)"
        return None

    def _check_dangerous_functions(self, stmt: exp.Expression) -> str | None:
        """检查危险函数调用

        Args:
            stmt: 解析后的语句

        Returns:
            错误消息或 None
        """
        for func in stmt.find_all(exp.Func):
            func_name = func.name.lower() if hasattr(func, 'name') else str(func.key).lower()
            if func_name in FORBIDDEN_FUNCTIONS:
                return f"Dangerous function '{func_name}' is not allowed"
        return None

    def _check_select_variants(self, stmt: exp.Expression) -> str | None:
        """检查危险的 SELECT 变体

        Args:
            stmt: 解析后的语句

        Returns:
            错误消息或 None
        """
        # 检查 INTO 子句 (SELECT INTO)
        if stmt.find(exp.Into):
            return "SELECT INTO is not allowed (creates tables)"

        # 检查 FOR UPDATE/SHARE 子句
        for _lock in stmt.find_all(exp.Lock):
            return "Locking clause is not allowed"

        return None

    def _check_subqueries(self, stmt: exp.Expression) -> str | None:
        """检查子查询和 CTE 中的修改操作

        Args:
            stmt: 解析后的语句

        Returns:
            错误消息或 None
        """
        # 检查 CTE
        for cte in stmt.find_all(exp.CTE):
            cte_query = cte.this
            if cte_query:
                for forbidden_type in FORBIDDEN_STATEMENT_TYPES:
                    if isinstance(cte_query, forbidden_type):
                        return f"CTE contains forbidden statement type: {cte_query.key}"

        # 检查子查询
        for subquery in stmt.find_all(exp.Subquery):
            inner = subquery.this
            if inner:
                for forbidden_type in FORBIDDEN_STATEMENT_TYPES:
                    if isinstance(inner, forbidden_type):
                        return f"Subquery contains forbidden statement type: {inner.key}"

        return None

    def validate_and_raise(self, sql: str) -> None:
        """验证 SQL 并在失败时抛出异常

        Args:
            sql: SQL 语句

        Raises:
            SQLSyntaxError: SQL 语法错误
            UnsafeSQLError: SQL 不安全
        """
        result = self.validate(sql)

        if not result.is_valid:
            raise SQLSyntaxError(sql, result.error_message or "Invalid SQL")

        if not result.is_safe:
            raise UnsafeSQLError(result.error_message or "Unsafe SQL")

    def add_limit(self, sql: str, limit: int) -> str:
        """为 SQL 添加 LIMIT 子句

        如果 SQL 已有 LIMIT，使用较小的值

        Args:
            sql: SQL 语句
            limit: 限制行数

        Returns:
            添加 LIMIT 后的 SQL
        """
        try:
            statements = self.parse(sql)
            if not statements:
                return sql

            stmt = statements[0]

            # 只对 SELECT 语句添加 LIMIT
            if not isinstance(stmt, exp.Select):
                return sql

            # 检查是否已有 LIMIT
            existing_limit = stmt.args.get("limit")
            if existing_limit:
                existing_value = int(existing_limit.this.this)
                if existing_value <= limit:
                    return sql
                # 替换为较小的值
                stmt.args["limit"] = exp.Limit(this=exp.Literal.number(limit))
            else:
                # 添加 LIMIT
                stmt = stmt.limit(limit)

            return stmt.sql(dialect=self.dialect)
        except Exception:
            # 解析失败时返回原始 SQL
            return sql

    def extract_tables(self, sql: str) -> list[str]:
        """提取 SQL 中引用的表名

        Args:
            sql: SQL 语句

        Returns:
            表名列表
        """
        try:
            statements = self.parse(sql)
            tables: set[str] = set()

            for stmt in statements:
                for table in stmt.find_all(exp.Table):
                    name = table.name
                    schema = table.db
                    if schema:
                        tables.add(f"{schema}.{name}")
                    else:
                        tables.add(name)

            return list(tables)
        except Exception:
            return []

    def normalize(self, sql: str) -> str:
        """规范化 SQL 格式

        Args:
            sql: SQL 语句

        Returns:
            规范化后的 SQL
        """
        try:
            statements = self.parse(sql)
            if statements:
                return statements[0].sql(dialect=self.dialect, pretty=True)
            return sql
        except Exception:
            return sql
