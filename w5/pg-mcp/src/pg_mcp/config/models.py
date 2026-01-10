from enum import Enum
from urllib.parse import quote_plus

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class SSLMode(str, Enum):
    """PostgreSQL SSL 模式"""
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"


class DatabaseConfig(BaseModel):
    """单个数据库连接配置"""
    name: str = Field(..., description="数据库别名，用于用户引用")

    # 方式一：分离参数
    host: str | None = None
    port: int = 5432
    database: str | None = None
    user: str | None = None
    password: SecretStr | None = None
    ssl_mode: SSLMode = SSLMode.PREFER

    # 方式二：连接字符串
    connection_string: SecretStr | None = None

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
        if self.connection_string:
            return self.connection_string.get_secret_value()

        password = quote_plus(self.password.get_secret_value()) if self.password else ""
        user = self.user or ""
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{self.database}"


class OpenAIConfig(BaseModel):
    """OpenAI 配置"""
    api_key: SecretStr = Field(..., description="OpenAI API Key")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    base_url: str | None = Field(default=None, description="自定义 API 地址")
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)


class RateLimitConfig(BaseModel):
    """速率限制配置"""
    enabled: bool = Field(default=True, description="是否启用速率限制")
    requests_per_minute: int = Field(default=60, ge=1, le=1000, description="每分钟最大请求数")
    requests_per_hour: int = Field(default=1000, ge=1, le=10000, description="每小时最大请求数")
    openai_tokens_per_minute: int = Field(
        default=100000, ge=1000, description="OpenAI 每分钟最大 token 数"
    )


class ServerConfig(BaseModel):
    """服务器配置"""
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
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="速率限制配置")


class AppConfig(BaseSettings):
    """应用程序总配置"""
    databases: list[DatabaseConfig] = Field(..., min_length=1)
    openai: OpenAIConfig
    server: ServerConfig = Field(default_factory=ServerConfig)

    model_config = {
        "env_prefix": "PG_MCP_",
        "env_nested_delimiter": "__",
    }

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
