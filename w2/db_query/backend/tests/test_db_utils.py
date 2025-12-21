"""Tests for database utility functions."""

import pytest

from src.utils.db_utils import detect_db_type, parse_mysql_url, mask_password, to_camel


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


class TestParseMySQLUrl:
    """Tests for parse_mysql_url function."""

    def test_parse_full_url(self) -> None:
        """Parse complete MySQL URL with all components."""
        url = "mysql://root:secret@localhost:3307/ecommerce"
        params = parse_mysql_url(url)

        assert params["host"] == "localhost"
        assert params["port"] == 3307
        assert params["user"] == "root"
        assert params["password"] == "secret"
        assert params["db"] == "ecommerce"

    def test_parse_url_without_password(self) -> None:
        """Parse MySQL URL without password."""
        url = "mysql://root@localhost:3306/mydb"
        params = parse_mysql_url(url)

        assert params["password"] == ""

    def test_parse_url_defaults(self) -> None:
        """Parse URL with defaults applied."""
        url = "mysql:///mydb"
        params = parse_mysql_url(url)

        assert params["host"] == "localhost"
        assert params["port"] == 3306
        assert params["user"] == "root"


class TestMaskPassword:
    """Tests for mask_password function."""

    def test_mask_postgresql_password(self) -> None:
        """PostgreSQL URL password should be masked."""
        url = "postgresql://user:secret@localhost:5432/db"
        masked = mask_password(url)
        assert masked == "postgresql://user:***@localhost:5432/db"

    def test_mask_mysql_password(self) -> None:
        """MySQL URL password should be masked."""
        url = "mysql://root:password123@localhost:3306/db"
        masked = mask_password(url)
        assert masked == "mysql://root:***@localhost:3306/db"

    def test_no_password_unchanged(self) -> None:
        """URL without password should be unchanged."""
        url = "postgresql://localhost:5432/db"
        masked = mask_password(url)
        assert masked == url

    def test_user_only_unchanged(self) -> None:
        """URL with user but no password should be unchanged."""
        url = "postgresql://user@localhost:5432/db"
        masked = mask_password(url)
        assert masked == url


class TestToCamel:
    """Tests for to_camel function."""

    def test_single_word(self) -> None:
        """Single word should remain unchanged."""
        assert to_camel("hello") == "hello"

    def test_two_words(self) -> None:
        """Two words should be camelCased."""
        assert to_camel("hello_world") == "helloWorld"

    def test_multiple_words(self) -> None:
        """Multiple words should be camelCased."""
        assert to_camel("my_variable_name") == "myVariableName"

    def test_already_lowercase(self) -> None:
        """Already lowercase single word."""
        assert to_camel("single") == "single"

    def test_database_fields(self) -> None:
        """Common database field names."""
        assert to_camel("created_at") == "createdAt"
        assert to_camel("updated_at") == "updatedAt"
        assert to_camel("is_primary_key") == "isPrimaryKey"
        assert to_camel("row_count") == "rowCount"
