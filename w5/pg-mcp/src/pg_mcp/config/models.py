"""Configuration models for PostgreSQL MCP Server.

This module provides configuration management using environment variables.
All configuration is read from environment variables with the PG_MCP_ prefix.

Environment Variables:
    Database Configuration (single database mode):
        PG_MCP_DATABASE_NAME: Database alias name (default: "main")
        PG_MCP_DATABASE_HOST: Database host
        PG_MCP_DATABASE_PORT: Database port (default: 5432)
        PG_MCP_DATABASE_DBNAME: Database name
        PG_MCP_DATABASE_USER: Database user
        PG_MCP_DATABASE_PASSWORD: Database password
        PG_MCP_DATABASE_URL: Connection string (overrides individual params)
        PG_MCP_DATABASE_SSL_MODE: SSL mode (disable/allow/prefer/require)
        PG_MCP_DATABASE_MIN_POOL_SIZE: Min pool size (default: 2)
        PG_MCP_DATABASE_MAX_POOL_SIZE: Max pool size (default: 10)

    OpenAI Configuration:
        PG_MCP_OPENAI_API_KEY: OpenAI API key (required)
        PG_MCP_OPENAI_MODEL: Model name (default: gpt-4o-mini)
        PG_MCP_OPENAI_BASE_URL: Custom API endpoint
        PG_MCP_OPENAI_MAX_RETRIES: Max retries (default: 3)
        PG_MCP_OPENAI_TIMEOUT: Request timeout in seconds (default: 30.0)

    Server Configuration:
        PG_MCP_SERVER_CACHE_REFRESH_INTERVAL: Schema cache refresh (default: 3600)
        PG_MCP_SERVER_MAX_RESULT_ROWS: Max rows to return (default: 1000)
        PG_MCP_SERVER_QUERY_TIMEOUT: Query timeout (default: 30.0)
        PG_MCP_SERVER_USE_READONLY_TRANSACTIONS: Enable read-only (default: true)
        PG_MCP_SERVER_MAX_SQL_RETRY: SQL retry count (default: 2)

    Rate Limit Configuration:
        PG_MCP_RATE_LIMIT_ENABLED: Enable rate limiting (default: true)
        PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE: RPM (default: 60)
        PG_MCP_RATE_LIMIT_REQUESTS_PER_HOUR: RPH (default: 1000)
"""

from enum import Enum
from urllib.parse import quote_plus

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSLMode(str, Enum):
    """PostgreSQL SSL 模式"""
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"


class DatabaseConfig(BaseModel):
    """单个数据库连接配置"""
    name: str = Field(default="main", description="数据库别名，用于用户引用")

    # 方式一：分离参数
    host: str | None = None
    port: int = 5432
    dbname: str | None = Field(default=None, description="数据库名称")
    user: str | None = None
    password: SecretStr | None = None
    ssl_mode: SSLMode = SSLMode.PREFER

    # SSL 证书配置
    ssl_verify_cert: bool = Field(
        default=True,
        description="验证 SSL 证书 (仅 REQUIRE 模式生效)"
    )
    ssl_ca_file: str | None = Field(
        default=None,
        description="CA 证书文件路径"
    )

    # 方式二：连接字符串
    url: SecretStr | None = Field(default=None, description="数据库连接字符串")

    # 连接池配置
    min_pool_size: int = Field(default=2, ge=1, le=20)
    max_pool_size: int = Field(default=10, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证数据库名称格式"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Database name must be alphanumeric with underscores/hyphens")
        return v.lower()

    def get_dsn(self) -> str:
        """获取数据库连接字符串"""
        if self.url:
            return self.url.get_secret_value()

        password = quote_plus(self.password.get_secret_value()) if self.password else ""
        user = self.user or ""
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{self.dbname}"


class OpenAISettings(BaseSettings):
    """OpenAI 配置 - 从环境变量读取"""
    api_key: SecretStr = Field(..., description="OpenAI API Key")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    base_url: str | None = Field(default=None, description="自定义 API 地址")
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)

    model_config = SettingsConfigDict(
        env_prefix="PG_MCP_OPENAI_",
        extra="ignore",
    )


class RateLimitSettings(BaseSettings):
    """速率限制配置 - 从环境变量读取"""
    enabled: bool = Field(default=True, description="是否启用速率限制")
    requests_per_minute: int = Field(default=60, ge=1, le=1000, description="每分钟最大请求数")
    requests_per_hour: int = Field(default=1000, ge=1, le=10000, description="每小时最大请求数")
    openai_tokens_per_minute: int = Field(
        default=100000, ge=1000, description="OpenAI 每分钟最大 token 数"
    )

    model_config = SettingsConfigDict(
        env_prefix="PG_MCP_RATE_LIMIT_",
        extra="ignore",
    )


class ServerSettings(BaseSettings):
    """服务器配置 - 从环境变量读取"""
    cache_refresh_interval: int = Field(
        default=3600, ge=60, description="Schema 缓存刷新间隔（秒）"
    )
    max_result_rows: int = Field(default=1000, ge=1, le=10000, description="最大返回行数")
    query_timeout: float = Field(default=30.0, ge=1.0, le=300.0, description="SQL 执行超时（秒）")
    enable_result_validation: bool = Field(default=False, description="启用 LLM 结果验证")
    max_sql_retry: int = Field(default=2, ge=0, le=5, description="SQL 语法错误时最大重试次数")
    use_readonly_transactions: bool = Field(
        default=True, description="深度防御：在只读事务中执行查询"
    )

    model_config = SettingsConfigDict(
        env_prefix="PG_MCP_SERVER_",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """数据库配置 - 从环境变量读取"""
    name: str = Field(default="main", description="数据库别名")
    host: str | None = Field(default=None, description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    dbname: str | None = Field(default=None, description="数据库名称")
    user: str | None = Field(default=None, description="数据库用户")
    password: SecretStr | None = Field(default=None, description="数据库密码")
    url: SecretStr | None = Field(default=None, description="数据库连接字符串")
    ssl_mode: SSLMode = Field(default=SSLMode.PREFER, description="SSL 模式")
    ssl_verify_cert: bool = Field(default=True, description="验证 SSL 证书")
    ssl_ca_file: str | None = Field(default=None, description="CA 证书文件路径")
    min_pool_size: int = Field(default=2, ge=1, le=20, description="最小连接池大小")
    max_pool_size: int = Field(default=10, ge=1, le=100, description="最大连接池大小")

    model_config = SettingsConfigDict(
        env_prefix="PG_MCP_DATABASE_",
        extra="ignore",
    )

    def to_database_config(self) -> DatabaseConfig:
        """转换为 DatabaseConfig"""
        return DatabaseConfig(
            name=self.name,
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            url=self.url,
            ssl_mode=self.ssl_mode,
            ssl_verify_cert=self.ssl_verify_cert,
            ssl_ca_file=self.ssl_ca_file,
            min_pool_size=self.min_pool_size,
            max_pool_size=self.max_pool_size,
        )


# Aliases for backward compatibility
OpenAIConfig = OpenAISettings
RateLimitConfig = RateLimitSettings
ServerConfig = ServerSettings


class AppConfig(BaseModel):
    """应用程序总配置

    This is the main configuration class that aggregates all settings.
    It can be created either from environment variables or manually.
    """
    databases: list[DatabaseConfig] = Field(..., min_length=1)
    openai: OpenAISettings
    server: ServerSettings = Field(default_factory=ServerSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    def get_database(self, name: str) -> DatabaseConfig | None:
        """根据名称获取数据库配置"""
        for db in self.databases:
            if db.name == name.lower():
                return db
        return None

    def get_default_database(self) -> DatabaseConfig:
        """获取默认数据库（第一个）"""
        return self.databases[0]

    @property
    def database_names(self) -> list[str]:
        """获取所有数据库名称"""
        return [db.name for db in self.databases]
