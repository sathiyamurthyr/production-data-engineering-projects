"""General-purpose helper functions."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex[:12]}" if prefix else uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def hash_dict(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def chunk_list(items: list, chunk_size: int) -> list[list]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def deep_get(d: dict, key_path: str, default: Any = None) -> Any:
    keys = key_path.split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d

