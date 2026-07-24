"""Configuration management for Python Fundamentals project."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseSettings, Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    This class demonstrates production-ready configuration management
    for data engineering applications.
    """

    # Application settings
    app_name: str = Field(default="python-fundamentals", env="APP_NAME")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Data settings
    batch_size: int = Field(default=1000, env="BATCH_SIZE", ge=1)
    data_directory: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "sample-data" / "raw",
        env="DATA_DIRECTORY",
    )

    # API settings
    api_timeout: int = Field(default=30, env="API_TIMEOUT", ge=1, le=300)
    api_max_retries: int = Field(default=3, env="API_MAX_RETRIES", ge=0, le=10)

    # Database settings
    database_url: str | None = Field(default=None, env="DATABASE_URL")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Invalid log level: {v}. Must be one of {allowed}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Invalid environment: {v}. Must be one of {allowed}")
        return v.lower()

    def get_config_dict(self) -> dict[str, Any]:
        """Return settings as dictionary for logging/configuration."""
        return {
            "app_name": self.app_name,
            "log_level": self.log_level,
            "environment": self.environment,
            "batch_size": self.batch_size,
            "data_directory": str(self.data_directory),
            "api_timeout": self.api_timeout,
            "api_max_retries": self.api_max_retries,
        }

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        yaml.YAMLError: If YAML parsing fails.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Global settings instance
settings = Settings()


def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value.

    Args:
        key: Setting attribute name.
        default: Default value if setting doesn't exist.

    Returns:
        Setting value or default.
    """
    return getattr(settings, key, default)