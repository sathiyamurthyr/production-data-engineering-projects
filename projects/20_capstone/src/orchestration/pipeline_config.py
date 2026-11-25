import os
import yaml
from pathlib import Path
from typing import Dict, Any

class PipelineConfig:
    """Manages platform configurations for the capstone data pipeline."""

    def __init__(self, config_path: str = None):
        if not config_path:
            # Default location relative to this file
            base_dir = Path(__file__).resolve().parents[2]
            config_path = base_dir / "configs" / "platform_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_yaml()
        self._override_with_env()

    def _load_yaml(self) -> Dict[str, Any]:
        """Loads yaml configuration, returns empty dict if file not found."""
        if not self.config_path.exists():
            print(f"Warning: Configuration file not found at {self.config_path}. Using defaults.")
            return {}
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f) or {}

    def _override_with_env(self):
        """Overrides yaml configurations with environment variables if present."""
        # Database credentials
        if "DB_HOST" in os.environ and "postgres" in self.config:
            self.config["postgres"] = self.config.get("postgres", {})
            self.config["postgres"]["host"] = os.environ["DB_HOST"]
        if "DB_USER" in os.environ:
            self.config["postgres"] = self.config.get("postgres", {})
            self.config["postgres"]["user"] = os.environ["DB_USER"]
        if "DB_PASSWORD" in os.environ:
            self.config["postgres"] = self.config.get("postgres", {})
            self.config["postgres"]["password"] = os.environ["DB_PASSWORD"]

        # Kafka broker
        if "KAFKA_BOOTSTRAP_SERVERS" in os.environ:
            self.config["kafka"] = self.config.get("kafka", {})
            self.config["kafka"]["bootstrap_servers"] = os.environ["KAFKA_BOOTSTRAP_SERVERS"].split(",")

        # Snowflake configuration
        if "SNOWFLAKE_ACCOUNT" in os.environ:
            self.config["snowflake"] = self.config.get("snowflake", {})
            self.config["snowflake"]["account"] = os.environ["SNOWFLAKE_ACCOUNT"]
        if "SNOWFLAKE_USER" in os.environ:
            self.config["snowflake"]["user"] = os.environ["SNOWFLAKE_USER"]
        if "SNOWFLAKE_PASSWORD" in os.environ:
            self.config["snowflake"]["password"] = os.environ["SNOWFLAKE_PASSWORD"]

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value by key."""
        return self.config.get(key, default)

    @property
    def kafka_config(self) -> Dict[str, Any]:
        return self.config.get("kafka", {})

    @property
    def storage_config(self) -> Dict[str, Any]:
        return self.config.get("storage", {})

    @property
    def spark_config(self) -> Dict[str, Any]:
        return self.config.get("spark", {})

    @property
    def snowflake_config(self) -> Dict[str, Any]:
        return self.config.get("snowflake", {})

    @property
    def data_quality_config(self) -> Dict[str, Any]:
        return self.config.get("data_quality", {})

    @property
    def api_config(self) -> Dict[str, Any]:
        return self.config.get("api", {})

    @property
    def alerting_config(self) -> Dict[str, Any]:
        return self.config.get("alerting", {})
