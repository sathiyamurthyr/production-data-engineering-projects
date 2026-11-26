"""
Pipeline Configuration Manager.
Reads JSON, YAML configs and injects Environment Variable overrides.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("pipeline.config")

class ConfigLoader:
    """Enterprise Configuration Manager."""
    
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            logger.warning(f"Config file {self.config_path} not found. Using default parameters.")
            return self._default_config()

        ext = self.config_path.suffix.lower()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                if ext == ".json":
                    data = json.load(f)
                elif ext in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = self._default_config()
        except Exception as e:
            logger.error(f"Error reading config file {self.config_path}: {e}")
            data = self._default_config()

        # Env Overrides
        data["environment"] = os.getenv("PIPELINE_ENV", data.get("environment", "production"))
        return data

    def _default_config(self) -> Dict[str, Any]:
        return {
            "environment": "production",
            "batch_size": 1000,
            "retry_attempts": 3,
            "backoff_factor": 2.0
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
