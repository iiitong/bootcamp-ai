import json
from typing import Any

import structlog
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from pg_mcp.config.models import OpenAIConfig
from pg_mcp.models.errors import OpenAIError
from pg_mcp.models.query import SQLGenerationResult
from pg_mcp.models.schema import DatabaseSchema

logger = structlog.get_logger(__name__)

# System prompt for SQL generation
SYSTEM_PROMPT = """You are a PostgreSQL expert. Your task is to convert natural \
language questions into accurate, safe, and efficient SQL queries.

Rules:
1. Only generate SELECT queries - no INSERT, UPDATE, DELETE, or DDL statements
2. Use proper table and column names from the provided schema
3. Add appropriate JOINs when querying related tables
4. Use parameterized patterns where appropriate
5. Include comments explaining complex logic
6. Optimize for performance when possible
7. Never use dangerous functions like pg_sleep, dblink, etc.
8. Do not use SELECT INTO, FOR UPDATE, or similar modifying clauses

Respond with a JSON object containing:
- "sql": The generated SQL query
- "explanation": A brief explanation of what the query does (optional)

If the question is ambiguous or cannot be answered with the given schema, \
explain why in the "explanation" field and set "sql" to null."""

USER_PROMPT_TEMPLATE = """Database Schema:
{schema}

Question: {question}

Generate a PostgreSQL query to answer this question."""


class OpenAIClient:
    """OpenAI API 客户端封装"""

    def __init__(self, config: OpenAIConfig) -> None:
        """初始化客户端

        Args:
            config: OpenAI 配置
        """
        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self._logger = logger.bind(model=config.model)

    async def generate_sql(
        self,
        question: str,
        schema: DatabaseSchema,
        error_context: str | None = None,
    ) -> SQLGenerationResult:
        """生成 SQL 查询

        Args:
            question: 自然语言问题
            schema: 数据库 Schema
            error_context: 之前生成的 SQL 错误信息（用于重试）

        Returns:
            SQL 生成结果

        Raises:
            OpenAIError: API 调用失败
        """
        self._logger.info(
            "Generating SQL",
            question=question[:100],
            database=schema.name,
            retry=error_context is not None,
        )

        # 构建用户消息
        user_message = USER_PROMPT_TEMPLATE.format(
            schema=schema.to_prompt_text(),
            question=question,
        )

        if error_context:
            user_message += (
                f"\n\nPrevious attempt failed with error: {error_context}\n"
                "Please fix the SQL query."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,  # type: ignore
                temperature=0,
                response_format={"type": "json_object"},
            )

            return self._parse_response(response)

        except Exception as e:
            self._logger.error("OpenAI API error", error=str(e))
            raise OpenAIError(str(e)) from e

    def _parse_response(self, response: ChatCompletion) -> SQLGenerationResult:
        """解析 API 响应

        Args:
            response: API 响应

        Returns:
            SQL 生成结果

        Raises:
            OpenAIError: 响应解析失败
        """
        try:
            content = response.choices[0].message.content
            if not content:
                raise OpenAIError("Empty response from OpenAI")

            data = json.loads(content)
            sql = data.get("sql")

            if not sql:
                explanation = data.get("explanation", "Unable to generate SQL")
                raise OpenAIError(f"No SQL generated: {explanation}")

            tokens_used = 0
            if response.usage:
                tokens_used = response.usage.total_tokens

            self._logger.info(
                "SQL generated successfully",
                tokens_used=tokens_used,
                sql_length=len(sql),
            )

            return SQLGenerationResult(
                sql=sql.strip(),
                explanation=data.get("explanation"),
                tokens_used=tokens_used,
            )

        except json.JSONDecodeError as e:
            self._logger.error("Failed to parse OpenAI response", error=str(e))
            raise OpenAIError(f"Invalid JSON response: {e}") from e

    async def validate_result(
        self,
        question: str,
        sql: str,
        result: list[dict[str, Any]],
    ) -> tuple[bool, str | None]:
        """验证查询结果是否合理（可选功能）

        Args:
            question: 原始问题
            sql: 执行的 SQL
            result: 查询结果

        Returns:
            (是否合理, 解释)
        """
        # 简化版验证，实际可以调用 LLM 来验证
        if not result:
            return True, "Empty result set"

        return True, None

    async def close(self) -> None:
        """关闭客户端"""
        await self._client.close()
