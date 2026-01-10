"""Unit tests for configuration module."""

from pathlib import Path

import pytest
import yaml

from pg_mcp.config.loader import expand_env_vars, load_config, process_config_dict
from pg_mcp.config.models import (
    DatabaseConfig,
    OpenAIConfig,
    RateLimitConfig,
    ServerConfig,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_valid_config(self) -> None:
        """Test creating valid database config."""
        config = DatabaseConfig(
            name="test_db",
            host="localhost",
            port=5432,
            database="test",
            user="postgres",
            password="secret",  # type: ignore
        )
        assert config.name == "test_db"
        assert config.host == "localhost"

    def test_name_validation(self) -> None:
        """Test database name validation."""
        config = DatabaseConfig(
            name="Test_DB-1",
            host="localhost",
            database="test",
            user="postgres",
        )
        assert config.name == "test_db-1"  # Lowercased

    def test_invalid_name(self) -> None:
        """Test that invalid names are rejected."""
        with pytest.raises(ValueError):
            DatabaseConfig(
                name="test@db",  # Invalid character
                host="localhost",
                database="test",
                user="postgres",
            )

    def test_get_dsn_from_parts(self) -> None:
        """Test DSN generation from parts."""
        config = DatabaseConfig(
            name="test",
            host="localhost",
            port=5432,
            database="mydb",
            user="user",
            password="pass",  # type: ignore
        )
        dsn = config.get_dsn()
        assert "postgresql://" in dsn
        assert "localhost" in dsn
        assert "5432" in dsn
        assert "mydb" in dsn

    def test_get_dsn_from_connection_string(self) -> None:
        """Test DSN from connection string."""
        config = DatabaseConfig(
            name="test",
            connection_string="postgresql://user:pass@host:5432/db",  # type: ignore
        )
        dsn = config.get_dsn()
        assert dsn == "postgresql://user:pass@host:5432/db"


class TestOpenAIConfig:
    """Tests for OpenAIConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = OpenAIConfig(api_key="sk-test")  # type: ignore
        assert config.model == "gpt-4o-mini"
        assert config.max_retries == 3
        assert config.timeout == 30.0


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = RateLimitConfig()
        assert config.enabled is True
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = ServerConfig()
        assert config.cache_refresh_interval == 3600
        assert config.max_result_rows == 1000
        assert config.use_readonly_transactions is True


class TestExpandEnvVars:
    """Tests for environment variable expansion."""

    def test_expand_simple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test simple variable expansion."""
        monkeypatch.setenv("TEST_VAR", "hello")
        result = expand_env_vars("${TEST_VAR}")
        assert result == "hello"

    def test_expand_with_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test expansion with default value."""
        monkeypatch.delenv("UNDEFINED_VAR", raising=False)
        result = expand_env_vars("${UNDEFINED_VAR:-default}")
        assert result == "default"

    def test_preserve_undefined(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that undefined vars without default are preserved."""
        monkeypatch.delenv("UNDEFINED_VAR", raising=False)
        result = expand_env_vars("${UNDEFINED_VAR}")
        assert result == "${UNDEFINED_VAR}"


class TestProcessConfigDict:
    """Tests for config dict processing."""

    def test_process_nested(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test processing nested config."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PASS", "secret")

        config = {
            "database": {
                "host": "${DB_HOST}",
                "password": "${DB_PASS}",
            }
        }
        result = process_config_dict(config)
        assert result["database"]["host"] == "localhost"
        assert result["database"]["password"] == "secret"

    def test_process_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test processing list values."""
        monkeypatch.setenv("DB_NAME", "test")

        config = {
            "databases": [
                {"name": "${DB_NAME}"},
            ]
        }
        result = process_config_dict(config)
        assert result["databases"][0]["name"] == "test"


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_from_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading config from file."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        config_data = {
            "databases": [
                {
                    "name": "test",
                    "host": "localhost",
                    "port": 5432,
                    "database": "testdb",
                    "user": "postgres",
                    "password": "pass",
                }
            ],
            "openai": {
                "api_key": "${OPENAI_API_KEY}",
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.databases[0].name == "test"
        assert config.openai.api_key.get_secret_value() == "sk-test"

    def test_load_missing_file(self) -> None:
        """Test that missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")
