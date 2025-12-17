"""Tests for database utility functions."""

import pytest

from src.utils.db_utils import detect_db_type


class TestDetectDbType:
    """Tests for detect_db_type function."""

    def test_postgresql_scheme(self) -> None:
        """postgresql:// should return 'postgresql'."""
        url = "postgresql://user:pass@localhost:5432/mydb"
        assert detect_db_type(url) == "postgresql"

    def test_postgres_scheme(self) -> None:
        """postgres:// should return 'postgresql'."""
        url = "postgres://user:pass@localhost:5432/mydb"
        assert detect_db_type(url) == "postgresql"

    def test_mysql_scheme(self) -> None:
        """mysql:// should return 'mysql'."""
        url = "mysql://root:pass@localhost:3306/mydb"
        assert detect_db_type(url) == "mysql"

    def test_mysql_aiomysql_scheme(self) -> None:
        """mysql+aiomysql:// should return 'mysql'."""
        url = "mysql+aiomysql://root:pass@localhost:3306/mydb"
        assert detect_db_type(url) == "mysql"

    def test_case_insensitive(self) -> None:
        """Scheme detection should be case-insensitive."""
        assert detect_db_type("POSTGRESQL://localhost/db") == "postgresql"
        assert detect_db_type("MySQL://localhost/db") == "mysql"
        assert detect_db_type("MYSQL+AIOMYSQL://localhost/db") == "mysql"

    def test_unsupported_scheme_raises(self) -> None:
        """Unsupported schemes should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported database type"):
            detect_db_type("mongodb://localhost/mydb")

        with pytest.raises(ValueError, match="Unsupported database type"):
            detect_db_type("sqlite:///path/to/db")

        with pytest.raises(ValueError, match="Unsupported database type"):
            detect_db_type("oracle://user:pass@localhost/db")

    def test_postgresql_without_password(self) -> None:
        """PostgreSQL URL without password should work."""
        url = "postgresql://user@localhost:5432/mydb"
        assert detect_db_type(url) == "postgresql"

    def test_mysql_without_password(self) -> None:
        """MySQL URL without password should work."""
        url = "mysql://root@localhost:3306/mydb"
        assert detect_db_type(url) == "mysql"

    def test_postgresql_minimal(self) -> None:
        """PostgreSQL URL with minimal info should work."""
        url = "postgresql://localhost/mydb"
        assert detect_db_type(url) == "postgresql"

    def test_mysql_minimal(self) -> None:
        """MySQL URL with minimal info should work."""
        url = "mysql://localhost/mydb"
        assert detect_db_type(url) == "mysql"
