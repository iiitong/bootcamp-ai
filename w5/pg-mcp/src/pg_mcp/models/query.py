from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReturnType(str, Enum):
    """查询返回类型"""
    SQL = "sql"
    RESULT = "result"
    BOTH = "both"


class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="自然语言查询需求")
    database: str | None = Field(default=None, description="目标数据库名称")
    return_type: ReturnType = Field(default=ReturnType.RESULT, description="返回类型")
    limit: int | None = Field(default=None, ge=1, le=10000, description="限制返回行数")


class QueryResult(BaseModel):
    """查询结果数据"""
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool = False


class QueryResponse(BaseModel):
    """查询成功响应"""
    success: bool = True
    sql: str | None = None
    result: QueryResult | None = None
    explanation: str | None = None
    validation: dict | None = None  # LLM-based result validation info


class SQLGenerationResult(BaseModel):
    """SQL 生成结果（内部使用）"""
    sql: str
    explanation: str | None = None
    tokens_used: int = 0


class SQLValidationResult(BaseModel):
    """SQL 验证结果（内部使用）"""
    is_valid: bool
    is_safe: bool
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)
