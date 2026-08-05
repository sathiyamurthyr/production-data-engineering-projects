"""Helper utility functions for data engineering patterns.

Provides common utilities used across all patterns:
- Request ID generation for tracing
- Safe dictionary access
- Deep merge of nested dictionaries
- String truncation for logging
"""

from __future__ import annotations

import uuid
from typing import Any


def generate_request_id() -> str:
    """Generate a unique request ID for tracing.

    Returns:
        A UUID4 string for request correlation.
    """
    return str(uuid.uuid4())


def safe_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a nested key from a dictionary using dot notation.

    Args:
        data: The dictionary to search.
        key: Dot-separated key path (e.g., 'user.profile.name').
        default: Default value if key not found.

    Returns:
        The value at the key path, or default.
    """
    keys = key.split(".")
    value: Any = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


def deep_merge(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary.
        override: Override dictionary whose values take precedence.

    Returns:
        A new merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def truncate_string(value: str, max_length: int = 100) -> str:
    """Truncate a string to a maximum length, appending ellipsis if truncated.

    Args:
        value: The string to truncate.
        max_length: Maximum length of the result (including ellipsis).

    Returns:
        Truncated string.
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
