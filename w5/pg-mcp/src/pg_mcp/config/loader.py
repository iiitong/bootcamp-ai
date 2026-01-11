"""Configuration loader for PostgreSQL MCP Server.

This module provides functions to load configuration from environment variables.
The primary method is load_config() which reads all settings from env vars.

Example usage:
    # Set environment variables:
    # PG_MCP_DATABASE_HOST=localhost
    # PG_MCP_DATABASE_DBNAME=mydb
    # PG_MCP_DATABASE_USER=postgres
    # PG_MCP_DATABASE_PASSWORD=secret
    # PG_MCP_OPENAI_API_KEY=sk-xxx

    from pg_mcp.config import load_config
    config = load_config()
"""

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    DatabaseSettings,
    OpenAISettings,
    RateLimitSettings,
    ServerSettings,
)


def load_config() -> AppConfig:
    """Load configuration from environment variables.

    This function reads all configuration from environment variables using
    pydantic-settings. Each settings class has its own env prefix:

    - PG_MCP_DATABASE_*: Database configuration
    - PG_MCP_OPENAI_*: OpenAI configuration
    - PG_MCP_SERVER_*: Server configuration
    - PG_MCP_RATE_LIMIT_*: Rate limit configuration

    Returns:
        AppConfig: Complete application configuration

    Raises:
        ValidationError: If required environment variables are missing or invalid
    """
    # Load settings from environment variables
    database_settings = DatabaseSettings()
    openai_settings = OpenAISettings()
    server_settings = ServerSettings()
    rate_limit_settings = RateLimitSettings()

    # Convert database settings to DatabaseConfig
    database_config = database_settings.to_database_config()

    # Create the complete configuration
    return AppConfig(
        databases=[database_config],
        openai=openai_settings,
        server=server_settings,
        rate_limit=rate_limit_settings,
    )


def load_config_from_dict(config_dict: dict) -> AppConfig:
    """Load configuration from a dictionary.

    This is useful for testing or when configuration comes from
    sources other than environment variables.

    Args:
        config_dict: Configuration dictionary

    Returns:
        AppConfig: Complete application configuration
    """
    databases = []
    for db_data in config_dict.get("databases", []):
        databases.append(DatabaseConfig(**db_data))

    return AppConfig(
        databases=databases,
        openai=OpenAISettings(**config_dict.get("openai", {})),
        server=ServerSettings(**config_dict.get("server", {})),
        rate_limit=RateLimitSettings(**config_dict.get("rate_limit", {})),
    )
