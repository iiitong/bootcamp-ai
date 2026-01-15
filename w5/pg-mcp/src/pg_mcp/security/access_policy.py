# src/pg_mcp/security/access_policy.py
"""Access policy executor for database security enforcement.

This module provides:
- Schema/table/column access validation
- SELECT * detection and handling
- Pattern-based column blocking
"""

import fnmatch
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

import structlog

from pg_mcp.config.models import (
    AccessPolicyConfig,
    SelectStarPolicy,
)
from pg_mcp.models.errors import ErrorCode, PgMcpError

if TYPE_CHECKING:
    from pg_mcp.infrastructure.sql_parser import ParsedSQLInfo


logger = structlog.get_logger()


class PolicyCheckResult(str, Enum):
    """Policy check result status."""

    PASSED = "passed"
    DENIED = "denied"
    WARNING = "warning"


@dataclass
class PolicyViolation:
    """Policy violation details."""

    check_type: str  # "schema", "table", "column", "explain"
    resource: str  # The denied resource
    reason: str  # Denial reason


class PolicyValidationResult(NamedTuple):
    """Policy validation result."""

    passed: bool
    violations: list[PolicyViolation]
    warnings: list[str]
    rewritten_sql: str | None = None  # Only used in filter mode


class TableAccessDeniedError(PgMcpError):
    """Table access denied error."""

    def __init__(self, tables: list[str]):
        super().__init__(
            ErrorCode.TABLE_ACCESS_DENIED,
            f"Access denied to tables: {', '.join(tables)}",
            {"denied_tables": tables},
        )


class ColumnAccessDeniedError(PgMcpError):
    """Column access denied error."""

    def __init__(self, columns: list[str], is_select_star: bool = False):
        message = f"Access denied to columns: {', '.join(columns)}"
        if is_select_star:
            message += " (triggered by SELECT *)"
        super().__init__(
            ErrorCode.COLUMN_ACCESS_DENIED,
            message,
            {"denied_columns": columns, "is_select_star": is_select_star},
        )


class SchemaAccessDeniedError(PgMcpError):
    """Schema access denied error."""

    def __init__(self, schema: str, allowed: list[str]):
        super().__init__(
            ErrorCode.SCHEMA_ACCESS_DENIED,
            f"Access denied to schema '{schema}'. Allowed: {', '.join(allowed)}",
            {"denied_schema": schema, "allowed_schemas": allowed},
        )


class DatabaseAccessPolicy:
    """
    Database access policy executor.

    Responsibilities:
    - Validate SQL access to Schema/tables/columns against policy
    - Detect SELECT * and handle according to policy
    - Support SQL rewriting (filter mode)
    """

    def __init__(self, config: AccessPolicyConfig):
        """Initialize the policy executor.

        Args:
            config: Access policy configuration
        """
        self.config = config
        self._compiled_patterns: list[re.Pattern[str]] = []
        self._compile_patterns()

        # Validate configuration consistency
        warnings = config.validate_consistency()
        for warning in warnings:
            logger.warning("access_policy_config_warning", warning=warning)

    def _compile_patterns(self) -> None:
        """Pre-compile column name patterns for matching."""
        for pattern in self.config.columns.denied_patterns:
            # Convert glob pattern to regex
            regex = fnmatch.translate(pattern.lower())
            self._compiled_patterns.append(re.compile(regex))

    def validate_schema(self, schema: str) -> PolicyValidationResult:
        """
        Validate schema access permission.

        Args:
            schema: Schema name

        Returns:
            PolicyValidationResult
        """
        schema_lower = schema.lower()
        allowed_schemas_lower = [s.lower() for s in self.config.allowed_schemas]

        if schema_lower not in allowed_schemas_lower:
            return PolicyValidationResult(
                passed=False,
                violations=[
                    PolicyViolation(
                        check_type="schema",
                        resource=schema,
                        reason=f"Schema not in allowed list: {self.config.allowed_schemas}",
                    )
                ],
                warnings=[],
            )
        return PolicyValidationResult(passed=True, violations=[], warnings=[])

    def validate_tables(self, tables: list[str]) -> PolicyValidationResult:
        """
        Validate table access permissions.

        Priority: allowed (whitelist) > denied (blacklist)

        Args:
            tables: Table name list

        Returns:
            PolicyValidationResult
        """
        violations = []
        tables_lower = [t.lower() for t in tables]

        allowed = [t.lower() for t in self.config.tables.allowed]
        denied = [t.lower() for t in self.config.tables.denied]

        for table in tables_lower:
            # Whitelist mode
            if allowed and table not in allowed:
                violations.append(
                    PolicyViolation(
                        check_type="table",
                        resource=table,
                        reason="Table not in allowed list",
                    )
                )
            # Blacklist mode
            elif not allowed and table in denied:
                violations.append(
                    PolicyViolation(
                        check_type="table",
                        resource=table,
                        reason="Table in denied list",
                    )
                )

        return PolicyValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=[],
        )

    def validate_columns(
        self,
        columns: list[tuple[str, str]],  # [(table, column), ...]
        is_select_star: bool = False,
    ) -> PolicyValidationResult:
        """
        Validate column access permissions.

        Args:
            columns: Column list, each item is (table, column) tuple
            is_select_star: Whether from SELECT * expansion

        Returns:
            PolicyValidationResult
        """
        violations = []
        denied_columns: list[str] = []

        denied_explicit = [c.lower() for c in self.config.columns.denied]

        for table, column in columns:
            full_name = f"{table.lower()}.{column.lower()}"

            # Check explicit denied list
            if full_name in denied_explicit:
                violations.append(
                    PolicyViolation(
                        check_type="column",
                        resource=full_name,
                        reason="Column in denied list",
                    )
                )
                denied_columns.append(full_name)
                continue

            # Check pattern matching
            for pattern in self._compiled_patterns:
                if pattern.match(full_name):
                    violations.append(
                        PolicyViolation(
                            check_type="column",
                            resource=full_name,
                            reason="Column matches denied pattern",
                        )
                    )
                    denied_columns.append(full_name)
                    break

        # Special handling for SELECT *
        if (
            is_select_star
            and violations
            and self.config.columns.select_star_policy == SelectStarPolicy.REJECT
        ):
            # Explicitly indicate which sensitive columns are triggered
            return PolicyValidationResult(
                passed=False,
                violations=violations,
                warnings=[f"SELECT * would access sensitive columns: {denied_columns}"],
            )

        return PolicyValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=[],
        )

    def get_safe_columns(self, table: str, all_columns: list[str]) -> list[str]:
        """
        Get safe column list for a table (used for SELECT * expansion).

        Args:
            table: Table name
            all_columns: All columns of the table

        Returns:
            List of safe columns
        """
        safe_columns = []
        denied_explicit = [c.lower() for c in self.config.columns.denied]

        for col in all_columns:
            full_name = f"{table.lower()}.{col.lower()}"

            # Check if in denied list
            if full_name in denied_explicit:
                continue

            # Check if matches denied pattern
            is_denied = False
            for pattern in self._compiled_patterns:
                if pattern.match(full_name):
                    is_denied = True
                    break

            if not is_denied:
                safe_columns.append(col)

        return safe_columns

    def validate_sql(self, parsed_result: "ParsedSQLInfo") -> PolicyValidationResult:
        """
        Complete SQL policy validation.

        Args:
            parsed_result: SQL parse result from sql_parser

        Returns:
            PolicyValidationResult
        """
        all_violations: list[PolicyViolation] = []
        all_warnings: list[str] = []

        # 1. Validate schemas
        for schema in parsed_result.schemas:
            result = self.validate_schema(schema)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)

        # 2. Validate tables
        result = self.validate_tables(parsed_result.tables)
        all_violations.extend(result.violations)
        all_warnings.extend(result.warnings)

        # 3. Validate columns
        result = self.validate_columns(
            parsed_result.columns, is_select_star=parsed_result.has_select_star
        )
        all_violations.extend(result.violations)
        all_warnings.extend(result.warnings)

        return PolicyValidationResult(
            passed=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
        )
