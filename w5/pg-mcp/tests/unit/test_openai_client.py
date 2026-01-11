# tests/unit/test_openai_client.py

"""OpenAI client unit tests."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from pg_mcp.config.models import OpenAISettings
from pg_mcp.infrastructure.openai_client import (
    OpenAIClient,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from pg_mcp.models.errors import OpenAIError
from pg_mcp.models.schema import ColumnInfo, DatabaseSchema, TableInfo


class TestSystemPrompt:
    """System prompt tests."""

    def test_system_prompt_contains_rules(self):
        """Test system prompt contains key rules."""
        assert "SELECT" in SYSTEM_PROMPT
        assert "INSERT" in SYSTEM_PROMPT or "no INSERT" in SYSTEM_PROMPT.lower()
        assert "pg_sleep" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT


class TestUserPromptTemplate:
    """User prompt template tests."""

    def test_template_has_placeholders(self):
        """Test template has required placeholders."""
        assert "{schema}" in USER_PROMPT_TEMPLATE
        assert "{question}" in USER_PROMPT_TEMPLATE

    def test_template_formatting(self):
        """Test template can be formatted."""
        result = USER_PROMPT_TEMPLATE.format(
            schema="Table: users (id, name)",
            question="Show all users"
        )

        assert "Table: users (id, name)" in result
        assert "Show all users" in result


class TestOpenAIClient:
    """OpenAI client tests."""

    @pytest.fixture
    def config(self) -> OpenAISettings:
        """Create test OpenAI config."""
        # Use patch to avoid .env loading during test
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-api-key"}):
            return OpenAISettings(
                api_key=SecretStr("test-api-key"),
                model="gpt-4o-mini",
                max_retries=3,
                timeout=30.0,
            )

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample database schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(
                            name="id",
                            data_type="integer",
                            is_nullable=False,
                            is_primary_key=True,
                        ),
                        ColumnInfo(
                            name="name",
                            data_type="varchar(100)",
                            is_nullable=False,
                        ),
                        ColumnInfo(
                            name="email",
                            data_type="varchar(255)",
                            is_nullable=False,
                        ),
                    ],
                ),
            ],
        )

    def test_client_initialization(self, config):
        """Test client initializes with correct config."""
        client = OpenAIClient(config)

        assert client.config == config
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_generate_sql_success(self, config, sample_schema):
        """Test successful SQL generation."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "sql": "SELECT * FROM users",
                        "explanation": "Fetches all users"
                    })
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=150)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await client.generate_sql("Show all users", sample_schema)

        assert result.sql == "SELECT * FROM users"
        assert result.explanation == "Fetches all users"
        assert result.tokens_used == 150

    @pytest.mark.asyncio
    async def test_generate_sql_strips_whitespace(self, config, sample_schema):
        """Test SQL is stripped of leading/trailing whitespace."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "sql": "  SELECT * FROM users  \n",
                    })
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=100)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await client.generate_sql("Show all users", sample_schema)

        assert result.sql == "SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_generate_sql_with_error_context(self, config, sample_schema):
        """Test SQL generation with error context for retry."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"sql": "SELECT * FROM users"})
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=100)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_create:
            await client.generate_sql(
                "Show all users",
                sample_schema,
                error_context="Previous SQL had syntax error"
            )

            # Verify error context was included in the message
            call_args = mock_create.call_args
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
            user_message = messages[1]["content"]
            assert "Previous attempt failed" in user_message
            assert "syntax error" in user_message

    @pytest.mark.asyncio
    async def test_generate_sql_empty_response(self, config, sample_schema):
        """Test handling of empty response."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=""))
        ]

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            with pytest.raises(OpenAIError) as exc_info:
                await client.generate_sql("Show all users", sample_schema)

            assert "Empty response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_sql_null_sql(self, config, sample_schema):
        """Test handling when SQL is null in response."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "sql": None,
                        "explanation": "Cannot generate SQL for this query"
                    })
                )
            )
        ]

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            with pytest.raises(OpenAIError) as exc_info:
                await client.generate_sql("Invalid query", sample_schema)

            assert "No SQL generated" in str(exc_info.value)
            assert "Cannot generate SQL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_sql_invalid_json(self, config, sample_schema):
        """Test handling of invalid JSON response."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Not valid JSON"))
        ]

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            with pytest.raises(OpenAIError) as exc_info:
                await client.generate_sql("Show all users", sample_schema)

            assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_sql_api_error(self, config, sample_schema):
        """Test API error handling."""
        client = OpenAIClient(config)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limit exceeded")
        ):
            with pytest.raises(OpenAIError) as exc_info:
                await client.generate_sql("Show all users", sample_schema)

            assert "API rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_sql_no_usage_info(self, config, sample_schema):
        """Test handling when usage info is missing."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"sql": "SELECT 1"})
                )
            )
        ]
        mock_response.usage = None

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await client.generate_sql("Test", sample_schema)

        assert result.tokens_used == 0

    @pytest.mark.asyncio
    async def test_generate_sql_uses_correct_model(self, config, sample_schema):
        """Test that correct model is used."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"sql": "SELECT 1"})
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=10)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_create:
            await client.generate_sql("Test", sample_schema)

            call_args = mock_create.call_args
            assert call_args.kwargs.get("model") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_generate_sql_temperature_zero(self, config, sample_schema):
        """Test that temperature is set to 0 for deterministic output."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"sql": "SELECT 1"})
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=10)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_create:
            await client.generate_sql("Test", sample_schema)

            call_args = mock_create.call_args
            assert call_args.kwargs.get("temperature") == 0

    @pytest.mark.asyncio
    async def test_generate_sql_json_response_format(self, config, sample_schema):
        """Test that JSON response format is requested."""
        client = OpenAIClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"sql": "SELECT 1"})
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=10)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_create:
            await client.generate_sql("Test", sample_schema)

            call_args = mock_create.call_args
            response_format = call_args.kwargs.get("response_format")
            assert response_format == {"type": "json_object"}


class TestValidateResult:
    """Result validation tests."""

    @pytest.fixture
    def config(self) -> OpenAISettings:
        """Create test OpenAI config."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-api-key"}):
            return OpenAISettings(
                api_key=SecretStr("test-api-key"),
                model="gpt-4o-mini",
            )

    @pytest.mark.asyncio
    async def test_validate_empty_result(self, config):
        """Test validation of empty result."""
        client = OpenAIClient(config)

        is_valid, explanation = await client.validate_result(
            question="Count users",
            sql="SELECT COUNT(*) FROM users",
            result=[]
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_non_empty_result(self, config):
        """Test validation of non-empty result."""
        client = OpenAIClient(config)

        is_valid, explanation = await client.validate_result(
            question="Get users",
            sql="SELECT * FROM users",
            result=[{"id": 1, "name": "Alice"}]
        )

        assert is_valid is True
