"""Unit tests for ConfigValidator."""

import tempfile

import pytest

from pg_mcp.config.validators import (
    ConfigValidator,
    ValidationResult,
    validate_config_command,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self) -> None:
        """Test that ValidationResult has correct default values."""
        result = ValidationResult(success=True)
        assert result.success is True
        assert result.errors == []
        assert result.warnings == []

    def test_with_errors_and_warnings(self) -> None:
        """Test ValidationResult with errors and warnings."""
        result = ValidationResult(
            success=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
        )
        assert result.success is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestConfigValidator:
    """Tests for ConfigValidator."""

    @pytest.fixture
    def validator(self) -> ConfigValidator:
        """Create a ConfigValidator instance."""
        return ConfigValidator()

    @pytest.fixture
    def valid_config_yaml(self) -> str:
        """Return valid YAML configuration content."""
        return """
databases:
  - name: test_db
    host: localhost
    port: 5432
    dbname: testdb
    user: postgres
    password: secret
    access_policy:
      allowed_schemas:
        - public
      tables:
        allowed: []
        denied: []
      columns:
        denied: []
        denied_patterns: []

openai:
  api_key: sk-test-key-1234567890
  model: gpt-4o-mini

server:
  cache_refresh_interval: 3600
  max_result_rows: 1000
  query_timeout: 30.0
"""

    def test_validate_nonexistent_file(self, validator: ConfigValidator) -> None:
        """Test validation of non-existent file."""
        result = validator.validate_file("/nonexistent/path/config.yaml")
        assert result.success is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    def test_validate_directory_instead_of_file(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation when path is a directory, not a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validator.validate_file(tmpdir)
            assert result.success is False
            assert "not a file" in result.errors[0].lower()

    def test_validate_invalid_yaml(self, validator: ConfigValidator) -> None:
        """Test validation of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [unbalanced")
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert len(result.errors) >= 1
        assert "yaml" in result.errors[0].lower()

    def test_validate_empty_file(self, validator: ConfigValidator) -> None:
        """Test validation of empty configuration file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert "empty" in result.errors[0].lower()

    def test_validate_invalid_config(self, validator: ConfigValidator) -> None:
        """Test validation of invalid configuration (missing required fields)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            # Missing required 'openai' field
            f.write("""
databases:
  - name: test_db
    host: localhost
    dbname: testdb
""")
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert len(result.errors) >= 1
        # Should mention missing openai field
        assert any("openai" in err.lower() for err in result.errors)

    def test_validate_valid_config(
        self, validator: ConfigValidator, valid_config_yaml: str
    ) -> None:
        """Test validation of valid configuration."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is True
        assert len(result.errors) == 0

    def test_validate_databases_duplicate_names(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation detects duplicate database names."""
        config_yaml = """
databases:
  - name: mydb
    host: localhost
    port: 5432
    dbname: database1
    user: user1
  - name: mydb
    host: localhost
    port: 5433
    dbname: database2
    user: user2

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert any("duplicate" in err.lower() for err in result.errors)

    def test_validate_databases_missing_connection_params(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation detects missing connection parameters."""
        config_yaml = """
databases:
  - name: test_db
    port: 5432
    user: postgres

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        # Should mention missing host and dbname
        assert any("host" in err.lower() for err in result.errors)
        assert any("dbname" in err.lower() for err in result.errors)

    def test_validate_databases_with_url(self, validator: ConfigValidator) -> None:
        """Test validation accepts URL-based connection."""
        config_yaml = """
databases:
  - name: test_db
    url: postgresql://user:pass@localhost:5432/mydb

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        # Should be valid (warnings are OK)
        assert result.success is True

    def test_validate_access_policy_conflicts(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation detects table policy conflicts."""
        config_yaml = """
databases:
  - name: test_db
    host: localhost
    dbname: testdb
    access_policy:
      allowed_schemas:
        - public
      tables:
        allowed:
          - users
          - orders
        denied:
          - users

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert any(
            "both allowed and denied" in err.lower() for err in result.errors
        )

    def test_validate_access_policy_warnings(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation generates warnings for overly permissive configs."""
        config_yaml = """
databases:
  - name: test_db
    host: localhost
    dbname: testdb
    access_policy:
      allowed_schemas:
        - public
      tables:
        allowed: []
        denied: []
      columns:
        denied_patterns:
          - "*.*.*.*"

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        # Should have warnings about broad patterns and no table restrictions
        assert len(result.warnings) >= 1
        assert any(
            "too broadly" in warning.lower() or "no table restrictions" in warning.lower()
            for warning in result.warnings
        )

    def test_validate_access_policy_all_columns_denied(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation warns when pattern denies all columns."""
        config_yaml = """
databases:
  - name: test_db
    host: localhost
    dbname: testdb
    access_policy:
      allowed_schemas:
        - public
      columns:
        denied_patterns:
          - "*.*"

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        # Should warn about denying all columns
        assert any(
            "deny all columns" in warning.lower() for warning in result.warnings
        )

    def test_validate_column_pattern_invalid_characters(
        self, validator: ConfigValidator
    ) -> None:
        """Test validation detects invalid characters in column patterns."""
        config_yaml = """
databases:
  - name: test_db
    host: localhost
    dbname: testdb
    access_policy:
      columns:
        denied_patterns:
          - "table@column"

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            result = validator.validate_file(f.name)

        assert result.success is False
        assert any("invalid characters" in err.lower() for err in result.errors)

    def test_print_validation_result_success(
        self, validator: ConfigValidator, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing successful validation result."""
        result = ValidationResult(success=True)
        validator.print_validation_result(result)

        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_print_validation_result_with_errors(
        self, validator: ConfigValidator, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing validation result with errors."""
        result = ValidationResult(
            success=False,
            errors=["Error 1", "Error 2"],
        )
        validator.print_validation_result(result)

        captured = capsys.readouterr()
        assert "errors" in captured.out.lower()
        assert "Error 1" in captured.out
        assert "Error 2" in captured.out

    def test_print_validation_result_with_warnings(
        self, validator: ConfigValidator, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing validation result with warnings."""
        result = ValidationResult(
            success=True,
            warnings=["Warning 1"],
        )
        validator.print_validation_result(result)

        captured = capsys.readouterr()
        assert "warnings" in captured.out.lower()
        assert "Warning 1" in captured.out


class TestValidateConfigCommand:
    """Tests for validate_config_command function."""

    def test_returns_zero_on_success(self) -> None:
        """Test command returns 0 on successful validation."""
        config_yaml = """
databases:
  - name: test_db
    host: localhost
    dbname: testdb

openai:
  api_key: sk-test-key-1234567890
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            exit_code = validate_config_command(f.name)

        assert exit_code == 0

    def test_returns_one_on_failure(self) -> None:
        """Test command returns 1 on validation failure."""
        exit_code = validate_config_command("/nonexistent/config.yaml")
        assert exit_code == 1

    def test_returns_one_on_invalid_config(self) -> None:
        """Test command returns 1 on invalid configuration."""
        config_yaml = """
databases: []
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            f.flush()
            exit_code = validate_config_command(f.name)

        assert exit_code == 1


class TestValidateColumnPattern:
    """Tests for _validate_column_pattern method."""

    @pytest.fixture
    def validator(self) -> ConfigValidator:
        """Create a ConfigValidator instance."""
        return ConfigValidator()

    def test_valid_exact_pattern(self, validator: ConfigValidator) -> None:
        """Test valid exact column pattern."""
        errors = validator._validate_column_pattern("users.password")
        assert errors == []

    def test_valid_wildcard_patterns(self, validator: ConfigValidator) -> None:
        """Test valid wildcard column patterns."""
        patterns = [
            "users.*",
            "*.password",
            "*._password*",
            "*.secret_*",
        ]
        for pattern in patterns:
            errors = validator._validate_column_pattern(pattern)
            assert errors == [], f"Pattern '{pattern}' should be valid"

    def test_empty_pattern(self, validator: ConfigValidator) -> None:
        """Test empty pattern is rejected."""
        errors = validator._validate_column_pattern("")
        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_whitespace_pattern(self, validator: ConfigValidator) -> None:
        """Test whitespace-only pattern is rejected."""
        errors = validator._validate_column_pattern("   ")
        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_invalid_characters(self, validator: ConfigValidator) -> None:
        """Test pattern with invalid characters is rejected."""
        invalid_patterns = [
            "table@column",
            "table#column",
            "table$column",
            "table column",
            "table;column",
        ]
        for pattern in invalid_patterns:
            errors = validator._validate_column_pattern(pattern)
            assert len(errors) > 0, f"Pattern '{pattern}' should be invalid"
            assert any("invalid characters" in err.lower() for err in errors)
