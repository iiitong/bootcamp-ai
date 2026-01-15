"""Serialization utilities for pg-mcp.

This module provides helper functions for safe model serialization
and sensitive data redaction.
"""

import re
from typing import Any

from pydantic import BaseModel, SecretStr

# Default patterns for sensitive field detection
DEFAULT_SENSITIVE_PATTERNS = [
    r".*password.*",
    r".*secret.*",
    r".*token.*",
    r".*api[_-]?key.*",
    r".*auth.*",
    r".*credential.*",
    r".*private[_-]?key.*",
]


def safe_model_dump(model: BaseModel, **kwargs: Any) -> dict[str, Any]:
    """Safely serialize a Pydantic model to dictionary.

    This is a wrapper around model_dump() that handles common edge cases:
    - Converts SecretStr to masked strings
    - Handles None values gracefully
    - Provides consistent serialization across the codebase

    Args:
        model: The Pydantic model to serialize
        **kwargs: Additional arguments passed to model_dump()

    Returns:
        Dictionary representation of the model
    """
    # Get the model dump with default serialization
    data = model.model_dump(**kwargs)

    # Post-process to mask SecretStr values
    return _mask_secrets(data, model)


def _is_secret_str_type(annotation: Any) -> bool:
    """Check if an annotation is SecretStr or Optional[SecretStr] / SecretStr | None.

    Args:
        annotation: The type annotation to check

    Returns:
        True if the annotation involves SecretStr
    """
    import types
    from typing import Union, get_args, get_origin

    # Direct SecretStr
    if annotation is SecretStr:
        return True

    # Handle Union types (Optional[SecretStr] or SecretStr | None)
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        return SecretStr in args

    return False


def _mask_secrets(data: dict[str, Any], model: BaseModel) -> dict[str, Any]:
    """Recursively mask SecretStr values in the dumped data.

    Args:
        data: The dictionary data to process
        model: The original Pydantic model for type inspection

    Returns:
        Dictionary with SecretStr values masked
    """
    result: dict[str, Any] = {}

    # Access model_fields from the class, not instance (Pydantic 2.11+ deprecation)
    model_fields = model.__class__.model_fields

    for key, value in data.items():
        # Check if the field in the model is a SecretStr
        field_info = model_fields.get(key)
        if field_info is not None:
            annotation = field_info.annotation
            # Handle Optional[SecretStr], SecretStr | None, and SecretStr
            if _is_secret_str_type(annotation):
                if value is not None:
                    result[key] = "***"
                else:
                    result[key] = None
                continue

        # Recursively process nested dicts
        if isinstance(value, dict):
            # Check if the field corresponds to a nested model
            attr_value = getattr(model, key, None)
            if isinstance(attr_value, BaseModel):
                result[key] = _mask_secrets(value, attr_value)
            else:
                result[key] = value
        elif isinstance(value, list):
            # Handle lists that may contain nested models
            attr_value = getattr(model, key, None)
            if isinstance(attr_value, list) and attr_value:
                result[key] = [
                    _mask_secrets(item, attr_value[i])
                    if isinstance(item, dict) and isinstance(attr_value[i], BaseModel)
                    else item
                    for i, item in enumerate(value)
                    if i < len(attr_value)
                ]
            else:
                result[key] = value
        else:
            result[key] = value

    return result


def redact_sensitive_fields(
    data: dict[str, Any],
    patterns: list[str] | None = None,
    redact_value: str = "***REDACTED***",
) -> dict[str, Any]:
    """Redact sensitive fields from a dictionary.

    Recursively scans the dictionary and redacts values whose keys match
    any of the provided patterns. Default patterns include common sensitive
    field names like password, secret, token, api_key, etc.

    Args:
        data: The dictionary to redact
        patterns: List of regex patterns to match field names (case-insensitive).
                 Defaults to common sensitive field patterns.
        redact_value: The value to replace sensitive fields with

    Returns:
        A new dictionary with sensitive values redacted

    Example:
        >>> data = {"user": "john", "password": "secret123", "api_key": "abc"}
        >>> redact_sensitive_fields(data)
        {"user": "john", "password": "***REDACTED***", "api_key": "***REDACTED***"}
    """
    if patterns is None:
        patterns = DEFAULT_SENSITIVE_PATTERNS

    # Compile patterns for efficiency
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    return _redact_recursive(data, compiled_patterns, redact_value)


def _redact_recursive(
    data: dict[str, Any],
    compiled_patterns: list[re.Pattern[str]],
    redact_value: str,
) -> dict[str, Any]:
    """Recursively redact sensitive fields from a dictionary.

    Args:
        data: The dictionary to process
        compiled_patterns: List of compiled regex patterns
        redact_value: The value to replace sensitive fields with

    Returns:
        A new dictionary with sensitive values redacted
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        # Check if this key matches any sensitive pattern
        is_sensitive = any(pattern.match(key) for pattern in compiled_patterns)

        if is_sensitive:
            result[key] = redact_value
        elif isinstance(value, dict):
            result[key] = _redact_recursive(value, compiled_patterns, redact_value)
        elif isinstance(value, list):
            result[key] = [
                _redact_recursive(item, compiled_patterns, redact_value)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result
