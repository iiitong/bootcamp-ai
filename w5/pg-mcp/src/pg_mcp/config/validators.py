"""Configuration validation utilities for pg-mcp.

This module provides tools for validating configuration files
before starting the server.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import structlog
import yaml
from pydantic import ValidationError

from pg_mcp.config.models import AccessPolicyConfig, AppConfig

logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """Validation result container."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ConfigValidator:
    """Configuration file validator.

    Responsibilities:
    - Validate configuration file syntax (YAML)
    - Check Pydantic model validation
    - Verify configuration consistency
    - Detect potential issues and generate warnings
    """

    def validate_file(self, config_path: str) -> ValidationResult:
        """Validate a configuration file.

        Args:
            config_path: Path to the configuration file

        Returns:
            ValidationResult with success status, errors and warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Check file exists
        path = Path(config_path)
        if not path.exists():
            return ValidationResult(
                success=False,
                errors=[f"Configuration file not found: {config_path}"],
            )

        if not path.is_file():
            return ValidationResult(
                success=False,
                errors=[f"Path is not a file: {config_path}"],
            )

        # 2. Parse YAML
        try:
            with open(path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return ValidationResult(
                success=False,
                errors=[f"Invalid YAML syntax: {e}"],
            )

        if raw_config is None:
            return ValidationResult(
                success=False,
                errors=["Configuration file is empty"],
            )

        if not isinstance(raw_config, dict):
            return ValidationResult(
                success=False,
                errors=["Configuration must be a YAML mapping (dictionary)"],
            )

        # 3. Validate with Pydantic
        try:
            config = AppConfig(**raw_config)
        except ValidationError as e:
            for error in e.errors():
                loc = ".".join(str(part) for part in error["loc"])
                msg = error["msg"]
                errors.append(f"{loc}: {msg}")
            return ValidationResult(success=False, errors=errors)

        # 4. Validate databases
        db_errors = self._validate_databases(config)
        errors.extend(db_errors)

        # 5. Validate access policies for each database
        for db in config.databases:
            policy_errors, policy_warnings = self._validate_access_policy(
                db.name, db.access_policy
            )
            errors.extend(policy_errors)
            warnings.extend(policy_warnings)

        success = len(errors) == 0
        return ValidationResult(success=success, errors=errors, warnings=warnings)

    def _validate_databases(self, config: AppConfig) -> list[str]:
        """Validate database configurations.

        Checks:
        - Database name uniqueness
        - Connection parameters
        """
        errors: list[str] = []

        # Check for duplicate database names
        db_names = [db.name for db in config.databases]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in db_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)

        if duplicates:
            errors.append(
                f"Duplicate database names: {', '.join(sorted(duplicates))}"
            )

        # Check connection parameters for each database
        for db in config.databases:
            if db.url is None:
                # When not using URL, host and dbname are required
                missing = []
                if not db.host:
                    missing.append("host")
                if not db.dbname:
                    missing.append("dbname")
                if missing:
                    errors.append(
                        f"Database '{db.name}' missing required fields: "
                        f"{', '.join(missing)} (or provide 'url')"
                    )

        return errors

    def _validate_access_policy(
        self,
        db_name: str,
        policy: AccessPolicyConfig,
    ) -> tuple[list[str], list[str]]:
        """Validate access policy configuration.

        Checks:
        - Policy consistency (no conflicts)
        - Overly permissive configurations
        - Column pattern validity

        Returns:
            Tuple of (errors, warnings)
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for table conflicts (tables in both allowed and denied)
        table_conflicts = set(policy.tables.allowed) & set(policy.tables.denied)
        if table_conflicts:
            errors.append(
                f"Database '{db_name}': Tables in both allowed and denied lists: "
                f"{', '.join(sorted(table_conflicts))}"
            )

        # Check column pattern validity
        for pattern in policy.columns.denied_patterns:
            pattern_errors = self._validate_column_pattern(pattern)
            for err in pattern_errors:
                errors.append(f"Database '{db_name}': {err}")

        # Generate warnings for overly broad patterns
        for pattern in policy.columns.denied_patterns:
            # Patterns with too many wildcards
            if pattern.count("*") > 2:
                warnings.append(
                    f"Database '{db_name}': Column pattern '{pattern}' "
                    "may match too broadly (more than 2 wildcards)"
                )
            # Pattern that matches all columns
            if pattern == "*.*" or pattern == "*":
                warnings.append(
                    f"Database '{db_name}': Column pattern '{pattern}' "
                    "will deny all columns"
                )

        # Warn if no schemas are allowed
        if not policy.allowed_schemas:
            warnings.append(
                f"Database '{db_name}': No schemas allowed in access policy"
            )

        # Warn if both table allowed list and denied list are empty
        # (means all tables are accessible)
        if not policy.tables.allowed and not policy.tables.denied:
            warnings.append(
                f"Database '{db_name}': No table restrictions configured, "
                "all tables will be accessible"
            )

        return errors, warnings

    def _validate_column_pattern(self, pattern: str) -> list[str]:
        """Validate a single column pattern.

        Valid patterns:
        - table.column (exact match)
        - table.* (all columns in table)
        - *.column (column in all tables)
        - *._password* (pattern matching)

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        # Pattern must not be empty
        if not pattern or pattern.isspace():
            errors.append("Empty column pattern is not allowed")
            return errors

        # Check for valid characters (alphanumeric, underscore, dot, asterisk)
        valid_pattern = r"^[a-zA-Z0-9_.*-]+$"
        if not re.match(valid_pattern, pattern):
            errors.append(
                f"Column pattern '{pattern}' contains invalid characters. "
                "Only alphanumeric, underscore, hyphen, dot, and asterisk are allowed."
            )

        return errors

    def print_validation_result(self, result: ValidationResult) -> None:
        """Print validation result to stdout.

        Format:
        - Configuration is valid (on success)
        - Configuration has errors: (on failure)
        Warnings: (if any)
        """
        if result.success:
            print("Configuration is valid")
        else:
            print("Configuration has errors:")
            for error in result.errors:
                print(f"  - {error}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")


def validate_config_command(config_path: str) -> int:
    """Entry point for the config validate command.

    Args:
        config_path: Path to configuration file

    Returns:
        Exit code (0=success, 1=failure)
    """
    validator = ConfigValidator()
    result = validator.validate_file(config_path)
    validator.print_validation_result(result)
    return 0 if result.success else 1
