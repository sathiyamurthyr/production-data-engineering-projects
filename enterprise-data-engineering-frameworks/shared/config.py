"""Configuration loader supporting YAML, JSON, env vars, and CLI overrides."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Hierarchical configuration loader."""
    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else None
        self._overrides: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        if self._config_path and self._config_path.exists():
            config = self._load_file(self._config_path)
        config = self._deep_merge(config, self._load_env())
        config = self._deep_merge(config, self._overrides)
        return config

    def override(self, key: str, value: Any) -> None:
        self._overrides[key] = value

    def _load_file(self, path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        content = path.read_text()
        if suffix in (".yaml", ".yml"):
            return yaml.safe_load(content) or {}
        elif suffix == ".json":
            return json.loads(content)
        return yaml.safe_load(content) or {}

    def _load_env(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith("EDF_"):
                parts = key[4:].lower().split("__")
                self._set_nested(config, parts, value)
        return config

    @staticmethod
    def _set_nested(d: dict, keys: list[str], value: Any) -> None:
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

