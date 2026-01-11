"""Unit tests for configuration module."""

import pytest

from pg_mcp.config.models import (
    DatabaseConfig,
    DatabaseSettings,
    OpenAISettings,
    RateLimitSettings,
    ServerSettings,
    SSLMode,
)
from pg_mcp.config.loader import load_config, load_config_from_dict


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_valid_config(self) -> None:
        """Test creating valid database config."""
        config = DatabaseConfig(
            name="test_db",
            host="localhost",
            port=5432,
            dbname="test",
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
            dbname="test",
            user="postgres",
        )
        assert config.name == "test_db-1"  # Lowercased

    def test_invalid_name(self) -> None:
        """Test that invalid names are rejected."""
        with pytest.raises(ValueError):
            DatabaseConfig(
                name="test@db",  # Invalid character
                host="localhost",
                dbname="test",
                user="postgres",
            )

    def test_get_dsn_from_parts(self) -> None:
        """Test DSN generation from parts."""
        config = DatabaseConfig(
            name="test",
            host="localhost",
            port=5432,
            dbname="mydb",
            user="user",
            password="pass",  # type: ignore
        )
        dsn = config.get_dsn()
        assert "postgresql://" in dsn
        assert "localhost" in dsn
        assert "5432" in dsn
        assert "mydb" in dsn

    def test_get_dsn_from_url(self) -> None:
        """Test DSN from URL."""
        config = DatabaseConfig(
            name="test",
            url="postgresql://user:pass@host:5432/db",  # type: ignore
        )
        dsn = config.get_dsn()
        assert dsn == "postgresql://user:pass@host:5432/db"


class TestDatabaseSettings:
    """Tests for DatabaseSettings from environment variables."""

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("PG_MCP_DATABASE_NAME", "testdb")
        monkeypatch.setenv("PG_MCP_DATABASE_HOST", "localhost")
        monkeypatch.setenv("PG_MCP_DATABASE_PORT", "5433")
        monkeypatch.setenv("PG_MCP_DATABASE_DBNAME", "mydb")
        monkeypatch.setenv("PG_MCP_DATABASE_USER", "testuser")
        monkeypatch.setenv("PG_MCP_DATABASE_PASSWORD", "secret")

        settings = DatabaseSettings()
        assert settings.name == "testdb"
        assert settings.host == "localhost"
        assert settings.port == 5433
        assert settings.dbname == "mydb"
        assert settings.user == "testuser"
        assert settings.password is not None
        assert settings.password.get_secret_value() == "secret"

    def test_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading URL from environment variable."""
        monkeypatch.setenv("PG_MCP_DATABASE_URL", "postgresql://u:p@h:5/d")

        settings = DatabaseSettings()
        config = settings.to_database_config()
        assert config.get_dsn() == "postgresql://u:p@h:5/d"

    def test_ssl_mode_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test SSL mode from environment variable."""
        monkeypatch.setenv("PG_MCP_DATABASE_SSL_MODE", "require")

        settings = DatabaseSettings()
        assert settings.ssl_mode == SSLMode.REQUIRE


class TestOpenAISettings:
    """Tests for OpenAISettings."""

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default values."""
        monkeypatch.setenv("PG_MCP_OPENAI_API_KEY", "sk-test")

        config = OpenAISettings()
        assert config.model == "gpt-4o-mini"
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("PG_MCP_OPENAI_API_KEY", "sk-mykey")
        monkeypatch.setenv("PG_MCP_OPENAI_MODEL", "gpt-4")
        monkeypatch.setenv("PG_MCP_OPENAI_TIMEOUT", "60.0")

        config = OpenAISettings()
        assert config.api_key.get_secret_value() == "sk-mykey"
        assert config.model == "gpt-4"
        assert config.timeout == 60.0


class TestRateLimitSettings:
    """Tests for RateLimitSettings."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = RateLimitSettings()
        assert config.enabled is True
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("PG_MCP_RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE", "120")

        config = RateLimitSettings()
        assert config.enabled is False
        assert config.requests_per_minute == 120


class TestServerSettings:
    """Tests for ServerSettings."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = ServerSettings()
        assert config.cache_refresh_interval == 3600
        assert config.max_result_rows == 1000
        assert config.use_readonly_transactions is True

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("PG_MCP_SERVER_MAX_RESULT_ROWS", "500")
        monkeypatch.setenv("PG_MCP_SERVER_QUERY_TIMEOUT", "60.0")
        monkeypatch.setenv("PG_MCP_SERVER_USE_READONLY_TRANSACTIONS", "false")

        config = ServerSettings()
        assert config.max_result_rows == 500
        assert config.query_timeout == 60.0
        assert config.use_readonly_transactions is False


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading complete config from environment variables."""
        # Database settings
        monkeypatch.setenv("PG_MCP_DATABASE_NAME", "test")
        monkeypatch.setenv("PG_MCP_DATABASE_HOST", "localhost")
        monkeypatch.setenv("PG_MCP_DATABASE_PORT", "5432")
        monkeypatch.setenv("PG_MCP_DATABASE_DBNAME", "testdb")
        monkeypatch.setenv("PG_MCP_DATABASE_USER", "postgres")
        monkeypatch.setenv("PG_MCP_DATABASE_PASSWORD", "pass")

        # OpenAI settings
        monkeypatch.setenv("PG_MCP_OPENAI_API_KEY", "sk-test")

        config = load_config()
        assert len(config.databases) == 1
        assert config.databases[0].name == "test"
        assert config.openai.api_key.get_secret_value() == "sk-test"

    def test_load_missing_required(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """Test that missing required env vars raise error."""
        import os

        # Clear all PG_MCP_ environment variables
        for key in list(os.environ.keys()):
            if key.startswith("PG_MCP_"):
                monkeypatch.delenv(key, raising=False)

        # Change to a temp directory without .env file to prevent auto-loading
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            with pytest.raises(Exception):  # ValidationError - OpenAI API key required
                load_config()
        finally:
            os.chdir(original_cwd)


class TestLoadConfigFromDict:
    """Tests for loading config from dictionary."""

    def test_load_valid_dict(self) -> None:
        """Test loading config from a valid dictionary."""
        config_dict = {
            "databases": [
                {
                    "name": "test",
                    "host": "localhost",
                    "port": 5432,
                    "dbname": "testdb",
                    "user": "postgres",
                    "password": "pass",
                }
            ],
            "openai": {
                "api_key": "sk-test",
            },
        }

        config = load_config_from_dict(config_dict)
        assert config.databases[0].name == "test"
        assert config.openai.api_key.get_secret_value() == "sk-test"

    def test_load_with_server_settings(self) -> None:
        """Test loading config with server settings."""
        config_dict = {
            "databases": [
                {
                    "name": "test",
                    "host": "localhost",
                    "dbname": "testdb",
                    "user": "postgres",
                }
            ],
            "openai": {
                "api_key": "sk-test",
            },
            "server": {
                "max_result_rows": 500,
                "query_timeout": 45.0,
            },
        }

        config = load_config_from_dict(config_dict)
        assert config.server.max_result_rows == 500
        assert config.server.query_timeout == 45.0
