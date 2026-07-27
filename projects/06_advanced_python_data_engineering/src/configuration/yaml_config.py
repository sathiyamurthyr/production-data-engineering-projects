"""
YAML Configuration Management for Data Engineering

Production patterns for configuration-driven pipelines.
"""

from pathlib import Path
from typing import Any
import yaml


class ConfigManager:
    """
    Configuration manager for data pipelines.
    
    Business Use Case: Environment-specific configuration loading.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, "r") as f:
            self._config = yaml.safe_load(f) or {}
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self) -> dict[str, Any]:
        """Reload configuration from file."""
        return self.load()


class EnvironmentConfig:
    """
    Environment-aware configuration loader.
    
    Business Use Case: Multi-environment pipeline deployment.
    """

    def __init__(
        self,
        base_path: str,
        environment: str = "dev",
    ) -> None:
        self.base_path = Path(base_path)
        self.environment = environment
        self._configs: dict[str, ConfigManager] = {}

    def load_all(self) -> dict[str, Any]:
        """Load all environment configurations."""
        merged_config: dict[str, Any] = {}

        # Load base config first
        base_file = self.base_path / "base.yaml"
        if base_file.exists():
            merged_config.update(ConfigManager(str(base_file)).load())

        # Override with environment-specific config
        env_file = self.base_path / f"{self.environment}.yaml"
        if env_file.exists():
            merged_config.update(ConfigManager(str(env_file)).load())

        return merged_config

    def get_db_config(self) -> dict[str, Any]:
        """Get database configuration."""
        return self.load_all().get("database", {})

    def get_api_config(self) -> dict[str, Any]:
        """Get API configuration."""
        return self.load_all().get("api", {})

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration."""
        return self.load_all().get("logging", {})