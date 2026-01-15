"""Unit tests for serialization utilities."""

import re
from typing import Any

from pydantic import BaseModel, SecretStr

from pg_mcp.utils.serialization import (
    DEFAULT_SENSITIVE_PATTERNS,
    redact_sensitive_fields,
    safe_model_dump,
)


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    value: int


class ModelWithSecret(BaseModel):
    """Model with SecretStr field for testing."""

    username: str
    password: SecretStr


class ModelWithOptionalSecret(BaseModel):
    """Model with optional SecretStr field for testing."""

    username: str
    api_key: SecretStr | None = None


class NestedModel(BaseModel):
    """Model with nested model containing secrets."""

    name: str
    credentials: ModelWithSecret


class ModelWithList(BaseModel):
    """Model with list of nested models."""

    name: str
    configs: list[ModelWithSecret]


class TestSafeModelDump:
    """Tests for safe_model_dump function."""

    def test_basic_model_dump(self) -> None:
        """Test basic model serialization without secrets."""
        model = SimpleModel(name="test", value=42)
        result = safe_model_dump(model)

        assert result == {"name": "test", "value": 42}

    def test_handles_secret_str(self) -> None:
        """Test that SecretStr values are masked."""
        model = ModelWithSecret(
            username="john",
            password=SecretStr("super_secret_password"),
        )
        result = safe_model_dump(model)

        assert result["username"] == "john"
        assert result["password"] == "***"
        assert "super_secret_password" not in str(result)

    def test_handles_optional_secret_str_with_value(self) -> None:
        """Test that optional SecretStr with value is masked."""
        model = ModelWithOptionalSecret(
            username="john",
            api_key=SecretStr("my_api_key"),
        )
        result = safe_model_dump(model)

        assert result["username"] == "john"
        assert result["api_key"] == "***"

    def test_handles_optional_secret_str_none(self) -> None:
        """Test that optional SecretStr with None value stays None."""
        model = ModelWithOptionalSecret(
            username="john",
            api_key=None,
        )
        result = safe_model_dump(model)

        assert result["username"] == "john"
        assert result["api_key"] is None

    def test_handles_nested_model_with_secrets(self) -> None:
        """Test that nested models with secrets are properly masked."""
        model = NestedModel(
            name="config",
            credentials=ModelWithSecret(
                username="admin",
                password=SecretStr("admin_password"),
            ),
        )
        result = safe_model_dump(model)

        assert result["name"] == "config"
        assert result["credentials"]["username"] == "admin"
        assert result["credentials"]["password"] == "***"

    def test_handles_list_of_models_with_secrets(self) -> None:
        """Test that lists of models with secrets are properly masked."""
        model = ModelWithList(
            name="multi_config",
            configs=[
                ModelWithSecret(username="user1", password=SecretStr("pass1")),
                ModelWithSecret(username="user2", password=SecretStr("pass2")),
            ],
        )
        result = safe_model_dump(model)

        assert result["name"] == "multi_config"
        assert len(result["configs"]) == 2
        assert result["configs"][0]["username"] == "user1"
        assert result["configs"][0]["password"] == "***"
        assert result["configs"][1]["username"] == "user2"
        assert result["configs"][1]["password"] == "***"

    def test_passes_kwargs_to_model_dump(self) -> None:
        """Test that kwargs are passed through to model_dump."""

        class ModelWithExclude(BaseModel):
            name: str
            internal_id: int
            password: SecretStr

        model = ModelWithExclude(
            name="test",
            internal_id=123,
            password=SecretStr("secret"),
        )
        result = safe_model_dump(model, exclude={"internal_id"})

        assert "name" in result
        assert "internal_id" not in result
        assert result["password"] == "***"

    def test_passes_include_to_model_dump(self) -> None:
        """Test that include kwarg works correctly."""
        model = SimpleModel(name="test", value=42)
        result = safe_model_dump(model, include={"name"})

        assert result == {"name": "test"}
        assert "value" not in result


class TestRedactSensitiveFields:
    """Tests for redact_sensitive_fields function."""

    def test_redacts_password_field(self) -> None:
        """Test that password fields are redacted."""
        data = {"username": "john", "password": "secret123"}
        result = redact_sensitive_fields(data)

        assert result["username"] == "john"
        assert result["password"] == "***REDACTED***"

    def test_redacts_api_key_field(self) -> None:
        """Test that api_key fields are redacted."""
        data = {"name": "config", "api_key": "sk-abc123"}
        result = redact_sensitive_fields(data)

        assert result["name"] == "config"
        assert result["api_key"] == "***REDACTED***"

    def test_redacts_api_key_with_hyphen(self) -> None:
        """Test that api-key fields are redacted."""
        data = {"name": "config", "api-key": "sk-abc123"}
        result = redact_sensitive_fields(data)

        assert result["api-key"] == "***REDACTED***"

    def test_redacts_token_field(self) -> None:
        """Test that token fields are redacted."""
        data = {"access_token": "eyJhbGc...", "refresh_token": "abc123"}
        result = redact_sensitive_fields(data)

        assert result["access_token"] == "***REDACTED***"
        assert result["refresh_token"] == "***REDACTED***"

    def test_redacts_secret_field(self) -> None:
        """Test that secret fields are redacted."""
        data = {"client_secret": "abc123", "secret_key": "xyz789"}
        result = redact_sensitive_fields(data)

        assert result["client_secret"] == "***REDACTED***"
        assert result["secret_key"] == "***REDACTED***"

    def test_redacts_auth_field(self) -> None:
        """Test that auth fields are redacted."""
        data = {"auth_token": "abc123", "authorization": "Bearer xyz"}
        result = redact_sensitive_fields(data)

        assert result["auth_token"] == "***REDACTED***"
        assert result["authorization"] == "***REDACTED***"

    def test_redacts_credential_field(self) -> None:
        """Test that credential fields are redacted."""
        data = {"credentials": "secret", "user_credential": "abc"}
        result = redact_sensitive_fields(data)

        assert result["credentials"] == "***REDACTED***"
        assert result["user_credential"] == "***REDACTED***"

    def test_redacts_private_key_field(self) -> None:
        """Test that private_key fields are redacted."""
        data = {"private_key": "-----BEGIN RSA PRIVATE KEY-----"}
        result = redact_sensitive_fields(data)

        assert result["private_key"] == "***REDACTED***"

    def test_redacts_nested_fields(self) -> None:
        """Test that nested sensitive fields are redacted."""
        data = {
            "user": "john",
            "database": {
                "host": "localhost",
                "password": "db_secret",
                "connection": {
                    "username": "admin",
                    "secret_key": "nested_secret",
                },
            },
        }
        result = redact_sensitive_fields(data)

        assert result["user"] == "john"
        assert result["database"]["host"] == "localhost"
        assert result["database"]["password"] == "***REDACTED***"
        assert result["database"]["connection"]["username"] == "admin"
        assert result["database"]["connection"]["secret_key"] == "***REDACTED***"

    def test_custom_patterns(self) -> None:
        """Test redaction with custom patterns."""
        data = {"ssn": "123-45-6789", "name": "John", "credit_card": "4111111111"}
        patterns = [r".*ssn.*", r".*credit.*"]
        result = redact_sensitive_fields(data, patterns=patterns)

        assert result["ssn"] == "***REDACTED***"
        assert result["name"] == "John"
        assert result["credit_card"] == "***REDACTED***"

    def test_custom_redact_value(self) -> None:
        """Test redaction with custom redact value."""
        data = {"password": "secret123"}
        result = redact_sensitive_fields(data, redact_value="[HIDDEN]")

        assert result["password"] == "[HIDDEN]"

    def test_leaves_non_sensitive_fields(self) -> None:
        """Test that non-sensitive fields are not modified."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "is_active": True,
            "tags": ["admin", "user"],
        }
        result = redact_sensitive_fields(data)

        assert result == data

    def test_handles_empty_dict(self) -> None:
        """Test handling of empty dictionary."""
        data: dict[str, Any] = {}
        result = redact_sensitive_fields(data)

        assert result == {}

    def test_handles_list_values(self) -> None:
        """Test handling of list values containing dictionaries."""
        data = {
            "users": [
                {"name": "john", "password": "pass1"},
                {"name": "jane", "password": "pass2"},
            ],
            "tags": ["admin", "user"],
        }
        result = redact_sensitive_fields(data)

        assert result["users"][0]["name"] == "john"
        assert result["users"][0]["password"] == "***REDACTED***"
        assert result["users"][1]["name"] == "jane"
        assert result["users"][1]["password"] == "***REDACTED***"
        assert result["tags"] == ["admin", "user"]

    def test_handles_deeply_nested_lists(self) -> None:
        """Test handling of deeply nested structures with lists."""
        data = {
            "configs": [
                {
                    "name": "db1",
                    "connections": [
                        {"host": "localhost", "password": "secret1"},
                        {"host": "remote", "password": "secret2"},
                    ],
                }
            ]
        }
        result = redact_sensitive_fields(data)

        assert result["configs"][0]["connections"][0]["host"] == "localhost"
        assert result["configs"][0]["connections"][0]["password"] == "***REDACTED***"
        assert result["configs"][0]["connections"][1]["password"] == "***REDACTED***"

    def test_case_insensitive_matching(self) -> None:
        """Test that pattern matching is case-insensitive."""
        data = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "password": "secret3",
            "API_KEY": "key1",
            "Api_Key": "key2",
        }
        result = redact_sensitive_fields(data)

        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Password"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"
        assert result["Api_Key"] == "***REDACTED***"

    def test_preserves_non_string_values(self) -> None:
        """Test that non-string sensitive values are still redacted."""
        data = {
            "password": 12345,  # numeric password (bad practice but should still redact)
            "count": 100,
        }
        result = redact_sensitive_fields(data)

        assert result["password"] == "***REDACTED***"
        assert result["count"] == 100


class TestDefaultSensitivePatterns:
    """Tests for DEFAULT_SENSITIVE_PATTERNS constant."""

    def test_patterns_are_valid_regex(self) -> None:
        """Test that all default patterns are valid regex."""
        for pattern in DEFAULT_SENSITIVE_PATTERNS:
            # Should not raise
            re.compile(pattern)

    def test_patterns_cover_common_cases(self) -> None:
        """Test that default patterns cover common sensitive field names."""
        test_cases = [
            ("password", True),
            ("user_password", True),
            ("secret", True),
            ("client_secret", True),
            ("token", True),
            ("access_token", True),
            ("api_key", True),
            ("apikey", True),
            ("api-key", True),
            ("auth_token", True),
            ("authorization", True),
            ("credentials", True),
            ("private_key", True),
            ("private-key", True),
            ("username", False),
            ("email", False),
            ("name", False),
            ("host", False),
        ]

        for field_name, should_match in test_cases:
            matched = any(
                re.match(pattern, field_name, re.IGNORECASE)
                for pattern in DEFAULT_SENSITIVE_PATTERNS
            )
            assert matched == should_match, (
                f"Field '{field_name}' should "
                f"{'match' if should_match else 'not match'} sensitive patterns"
            )
