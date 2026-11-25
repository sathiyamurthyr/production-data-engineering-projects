"""
Pipeline configuration management module for loading and validating YAML settings.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml

from src.pipeline.pipeline_logger import setup_logger

logger = setup_logger("etl_pipeline.config")


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class PipelineConfig:
    """Wrapper and parser for ETL pipeline YAML configurations."""

    def __init__(self, config_path: Union[str, Path]):
        """
        Load and initialize configuration object from a YAML file.

        Args:
            config_path: Path to YAML configuration file.

        Raises:
            ConfigurationError: If config file is missing or unparseable.
        """
        self.config_path = Path(config_path)
        self.raw_config: Dict[str, Any] = self._load_yaml()
        self._validate_structure()

    def _load_yaml(self) -> Dict[str, Any]:
        """Read and parse YAML configuration file."""
        if not self.config_path.exists():
            msg = f"Configuration file not found: {self.config_path}"
            logger.error(msg)
            raise ConfigurationError(msg)

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if not isinstance(content, dict):
                    raise ConfigurationError(f"YAML content in '{self.config_path}' must be a key-value dictionary.")
                logger.info(f"Loaded pipeline configuration from {self.config_path}")
                return content
        except Exception as e:
            msg = f"Error parsing YAML file '{self.config_path}': {str(e)}"
            logger.error(msg)
            raise ConfigurationError(msg) from e

    def _validate_structure(self) -> None:
        """Ensure required top-level configuration sections are present."""
        required_sections = ["pipeline", "extractors", "transformers", "loaders"]
        missing = [sec for sec in required_sections if sec not in self.raw_config]
        if missing:
            msg = f"Configuration missing required sections: {missing}"
            logger.error(msg)
            raise ConfigurationError(msg)

    @property
    def pipeline_settings(self) -> Dict[str, Any]:
        """Return general pipeline settings."""
        return self.raw_config.get("pipeline", {})

    @property
    def extractors_config(self) -> Dict[str, Any]:
        """Return extractor configurations."""
        return self.raw_config.get("extractors", {})

    @property
    def transformers_config(self) -> Dict[str, Any]:
        """Return transformer configurations."""
        return self.raw_config.get("transformers", {})

    @property
    def loaders_config(self) -> Dict[str, Any]:
        """Return loader configurations."""
        return self.raw_config.get("loaders", {})

    def get_extractor_setting(self, extractor_name: str) -> Dict[str, Any]:
        """Get settings for specific named extractor."""
        if extractor_name not in self.extractors_config:
            raise ConfigurationError(f"Extractor '{extractor_name}' not defined in config.")
        return self.extractors_config[extractor_name]

    def get_loader_setting(self, loader_name: str) -> Dict[str, Any]:
        """Get settings for specific named loader."""
        if loader_name not in self.loaders_config:
            raise ConfigurationError(f"Loader '{loader_name}' not defined in config.")
        return self.loaders_config[loader_name]
