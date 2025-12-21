"""Pytest fixtures for integration tests."""

import os

import pytest


@pytest.fixture
def mysql_url() -> str:
    """Get MySQL connection URL from environment.

    Set TEST_MYSQL_URL environment variable to run MySQL integration tests.
    Example: TEST_MYSQL_URL=mysql://user:pass@localhost:3306/testdb

    Returns:
        MySQL connection URL

    Raises:
        pytest.skip: If TEST_MYSQL_URL is not set
    """
    url = os.getenv("TEST_MYSQL_URL")
    if not url:
        pytest.skip("TEST_MYSQL_URL not set - skipping MySQL integration tests")
    return url


@pytest.fixture
def postgres_url() -> str:
    """Get PostgreSQL connection URL from environment.

    Set TEST_POSTGRES_URL environment variable to run PostgreSQL integration tests.
    Example: TEST_POSTGRES_URL=postgresql://user:pass@localhost:5432/testdb

    Returns:
        PostgreSQL connection URL

    Raises:
        pytest.skip: If TEST_POSTGRES_URL is not set
    """
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL not set - skipping PostgreSQL integration tests")
    return url
