"""Configuration management for Enterprise Data Engineering Patterns.

Provides a Pydantic-based configuration model with:
- Environment variable loading
- Validation and defaults
- Nested configuration support
- Serialization
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PatternConfig(BaseSettings):
    """Base configuration for all data engineering patterns.

    All pattern configurations inherit from this base class,
    ensuring consistent configuration management across the repository.
    """

    model_config = SettingsConfigDict(
        env_prefix="PATTERN_",
        env_nested_delimiter="__",
        extra="allow",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Environment
    environment: str = Field(default="development", description="Runtime environment")

    # Data paths
    data_dir: Path = Field(default=Path("./data"), description="Data directory")
    temp_dir: Path = Field(default=Path("./tmp"), description="Temporary directory")

    # Feature flags
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValueError(
                f"Invalid environment: {v}. Must be one of {valid_envs}"
            )
        return v.lower()


def load_config(config_class: type[PatternConfig] | None = None) -> PatternConfig:
    """Load configuration from environment variables.

    Args:
        config_class: Configuration class to instantiate. Defaults to PatternConfig.

    Returns:
        Configured PatternConfig instance.
    """
    if config_class is None:
        config_class = PatternConfig
    return config_class()


def get_env(name: str, default: str | None = None) -> str | None:
    """Get an environment variable.

    Args:
        name: Environment variable name.
        default: Default value if not set.

    Returns:
        Environment variable value or default.
    """
    return os.environ.get(name, default)


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value from the config or environment.

    Args:
        key: Configuration key.
        default: Default value.

    Returns:
        Configuration value or default.
    """
    return os.environ.get(key.upper(), default)
