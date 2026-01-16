# tests/unit/test_result_validator.py

"""Result validator unit tests."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.services.result_validator import (
    ResultValidator,
    ResultValidatorConfig,
    ValidationResult,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT_TEMPLATE,
)


class TestValidationResult:
    """ValidationResult model tests."""

    def test_valid_result(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            confidence=0.95,
            explanation="Result matches the user intent.",
        )
        assert result.is_valid is True
        assert result.confidence == 0.95
        assert "matches" in result.explanation

    def test_invalid_result(self):
        """Test creating an invalid ValidationResult."""
        result = ValidationResult(
            is_valid=False,
            confidence=0.8,
            explanation="Result does not match user intent.",
        )
        assert result.is_valid is False
        assert result.confidence == 0.8

    def test_confidence_bounds_validation(self):
        """Test confidence bounds are enforced."""
        # Valid bounds
        result = ValidationResult(is_valid=True, confidence=0.0, explanation="test")
        assert result.confidence == 0.0

        result = ValidationResult(is_valid=True, confidence=1.0, explanation="test")
        assert result.confidence == 1.0

        # Invalid bounds should raise validation error
        with pytest.raises(ValueError):
            ValidationResult(is_valid=True, confidence=-0.1, explanation="test")

        with pytest.raises(ValueError):
            ValidationResult(is_valid=True, confidence=1.1, explanation="test")


class TestValidationPrompts:
    """Prompt template tests."""

    def test_system_prompt_contains_key_elements(self):
        """Test system prompt contains necessary guidance."""
        assert "validator" in VALIDATION_SYSTEM_PROMPT.lower()
        assert "is_valid" in VALIDATION_SYSTEM_PROMPT
        assert "confidence" in VALIDATION_SYSTEM_PROMPT
        assert "explanation" in VALIDATION_SYSTEM_PROMPT
        assert "JSON" in VALIDATION_SYSTEM_PROMPT

    def test_user_prompt_has_placeholders(self):
        """Test user prompt template has required placeholders."""
        assert "{user_intent}" in VALIDATION_USER_PROMPT_TEMPLATE
        assert "{query}" in VALIDATION_USER_PROMPT_TEMPLATE
        assert "{result_summary}" in VALIDATION_USER_PROMPT_TEMPLATE
        assert "{row_count}" in VALIDATION_USER_PROMPT_TEMPLATE

    def test_user_prompt_formatting(self):
        """Test user prompt can be formatted correctly."""
        result = VALIDATION_USER_PROMPT_TEMPLATE.format(
            user_intent="Show all users",
            query="SELECT * FROM users",
            row_count=5,
            truncated_note="",
            result_summary='[{"id": 1, "name": "Alice"}]',
        )
        assert "Show all users" in result
        assert "SELECT * FROM users" in result
        assert "5 rows" in result


class TestResultValidatorConfig:
    """ResultValidatorConfig tests."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ResultValidatorConfig()
        assert config.timeout == 30.0
        assert config.max_result_rows_for_validation == 20
        assert config.max_result_chars == 4000

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ResultValidatorConfig(
            timeout=60.0,
            max_result_rows_for_validation=50,
            max_result_chars=8000,
        )
        assert config.timeout == 60.0
        assert config.max_result_rows_for_validation == 50
        assert config.max_result_chars == 8000


class TestResultValidator:
    """ResultValidator tests."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def validator(self, mock_openai_client):
        """Create ResultValidator with mock client."""
        return ResultValidator(
            client=mock_openai_client,
            model="gpt-4o-mini",
        )

    @pytest.fixture
    def validator_with_config(self, mock_openai_client):
        """Create ResultValidator with custom config."""
        config = ResultValidatorConfig(
            timeout=5.0,
            max_result_rows_for_validation=10,
            max_result_chars=2000,
        )
        return ResultValidator(
            client=mock_openai_client,
            model="gpt-4o-mini",
            config=config,
        )

    def test_initialization(self, mock_openai_client):
        """Test validator initialization."""
        validator = ResultValidator(
            client=mock_openai_client,
            model="gpt-4o-mini",
        )
        assert validator._client == mock_openai_client
        assert validator._model == "gpt-4o-mini"
        assert validator._config is not None

    def test_initialization_with_config(self, mock_openai_client):
        """Test validator initialization with custom config."""
        config = ResultValidatorConfig(timeout=10.0)
        validator = ResultValidator(
            client=mock_openai_client,
            model="gpt-4o-mini",
            config=config,
        )
        assert validator._config.timeout == 10.0

    @pytest.mark.asyncio
    async def test_validate_empty_result(self, validator):
        """Test validation of empty results."""
        result = await validator.validate_result(
            query="SELECT * FROM users WHERE id = 999",
            user_intent="Find user with ID 999",
            result=[],
        )

        assert result.is_valid is True
        assert result.confidence == 0.8
        assert "empty" in result.explanation.lower()

        # API should not be called for empty results
        validator._client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_success(self, validator, mock_openai_client):
        """Test successful validation."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 0.95,
                        "explanation": "The result correctly lists all users.",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        )

        assert result.is_valid is True
        assert result.confidence == 0.95
        assert "correctly" in result.explanation

    @pytest.mark.asyncio
    async def test_validate_invalid_result(self, validator, mock_openai_client):
        """Test validation that finds result invalid."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": False,
                        "confidence": 0.85,
                        "explanation": "Result shows orders but user asked for users.",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await validator.validate_result(
            query="SELECT * FROM orders",
            user_intent="Show all users",
            result=[{"id": 1, "order_id": 100}],
        )

        assert result.is_valid is False
        assert result.confidence == 0.85
        assert "orders" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_validate_large_result_truncated(
        self, validator_with_config, mock_openai_client
    ):
        """Test that large results are truncated."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 0.9,
                        "explanation": "Result appears valid.",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Create 50 rows (more than the 10 row limit in config)
        large_result = [{"id": i, "name": f"User {i}"} for i in range(50)]

        result = await validator_with_config.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=large_result,
        )

        assert result.is_valid is True

        # Verify API was called with truncated note
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", call_args[1].get("messages", []))
        user_message = messages[1]["content"]
        assert "truncated" in user_message.lower()

    @pytest.mark.asyncio
    async def test_validate_timeout_handling(self, mock_openai_client):
        """Test timeout handling."""
        # Create validator with very short timeout
        config = ResultValidatorConfig(timeout=0.001)  # 1ms timeout
        validator = ResultValidator(
            client=mock_openai_client,
            model="gpt-4o-mini",
            config=config,
        )

        # Make the API call take longer than timeout
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(1)  # 1 second, much longer than timeout
            return MagicMock()

        mock_openai_client.chat.completions.create.side_effect = slow_response

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        # Should return safe default on timeout
        assert result.is_valid is True
        assert result.confidence == 0.5
        assert "timed out" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_validate_api_error_handling(self, validator, mock_openai_client):
        """Test API error handling."""
        mock_openai_client.chat.completions.create.side_effect = Exception(
            "API rate limit exceeded"
        )

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        # Should return safe default on error
        assert result.is_valid is True
        assert result.confidence == 0.5
        assert "error" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_validate_empty_response(self, validator, mock_openai_client):
        """Test handling of empty response content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        # Should return safe default for empty response
        assert result.is_valid is True
        assert result.confidence == 0.5
        assert "empty" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_validate_invalid_json_response(self, validator, mock_openai_client):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Not valid JSON"))
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        # Should return safe default for invalid JSON
        assert result.is_valid is True
        assert result.confidence == 0.5
        assert "parse" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_validate_confidence_clamping(self, validator, mock_openai_client):
        """Test that confidence is clamped to [0, 1]."""
        # Test confidence > 1 (should be clamped)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 1.5,  # Invalid, should be clamped to 1.0
                        "explanation": "Very confident",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        assert result.confidence == 1.0

        # Test confidence < 0 (should be clamped)
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": -0.5,  # Invalid, should be clamped to 0.0
                        "explanation": "Not confident",
                    })
                )
            )
        ]

        result = await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1, "name": "Alice"}],
        )

        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_validate_uses_correct_model(self, validator, mock_openai_client):
        """Test that the correct model is used."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 0.9,
                        "explanation": "Valid",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1}],
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs.get("model") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_validate_uses_json_response_format(
        self, validator, mock_openai_client
    ):
        """Test that JSON response format is requested."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 0.9,
                        "explanation": "Valid",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1}],
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        response_format = call_args.kwargs.get("response_format")
        assert response_format == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_validate_temperature_zero(self, validator, mock_openai_client):
        """Test that temperature is set to 0 for deterministic output."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "is_valid": True,
                        "confidence": 0.9,
                        "explanation": "Valid",
                    })
                )
            )
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        await validator.validate_result(
            query="SELECT * FROM users",
            user_intent="Show all users",
            result=[{"id": 1}],
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs.get("temperature") == 0


class TestResultValidatorPrepareResultSummary:
    """Tests for _prepare_result_summary method."""

    @pytest.fixture
    def validator(self):
        """Create validator with mock client."""
        mock_client = MagicMock()
        return ResultValidator(
            client=mock_client,
            model="gpt-4o-mini",
        )

    def test_small_result_not_truncated(self, validator):
        """Test that small results are not truncated."""
        result = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        summary, truncated = validator._prepare_result_summary(result)

        assert truncated is False
        assert "Alice" in summary
        assert "Bob" in summary

    def test_large_row_count_truncated(self, validator):
        """Test that results with many rows are truncated."""
        # Default max is 20 rows
        result = [{"id": i, "name": f"User {i}"} for i in range(50)]
        summary, truncated = validator._prepare_result_summary(result)

        assert truncated is True
        assert "User 0" in summary  # First row should be present
        assert "User 19" in summary  # 20th row should be present
        assert "User 49" not in summary  # 50th row should not be present

    def test_large_content_truncated(self, validator):
        """Test that results with large content are truncated."""
        # Create result with very long strings
        result = [{"data": "x" * 5000}]
        summary, truncated = validator._prepare_result_summary(result)

        assert truncated is True
        assert "truncated" in summary.lower()
        assert len(summary) <= validator._config.max_result_chars + 20  # Allow for "... (truncated)"

    def test_non_json_serializable_fallback(self, validator):
        """Test fallback for non-JSON-serializable objects."""

        class CustomObject:
            def __str__(self):
                return "custom_object"

        result = [{"obj": CustomObject()}]
        summary, truncated = validator._prepare_result_summary(result)

        # Should fall back to string representation
        assert "custom_object" in summary
