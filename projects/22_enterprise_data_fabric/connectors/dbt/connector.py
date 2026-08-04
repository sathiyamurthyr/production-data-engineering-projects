"""dbt Connector - dbt metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class DbtConnector(BaseConnector):
    """Harvest metadata from dbt."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize dbt connector."""
        super().__init__(config)
        self.platform_name = "dbt"
        self.dbt_project_path = config.get("dbt_project_path", ".")
        self.target = config.get("target", "dev")
        self.profiles_dir = config.get("profiles_dir", "~/.dbt")
        self.adapter = config.get("adapter", "snowflake")

    def test_connection(self) -> bool:
        """Test connection to dbt."""
        try:
            # In production, run dbt debug
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all dbt models."""
        assets = []
        try:
            # In production, parse dbt manifest.json
            # manifest = json.load(open(f"{self.dbt_project_path}/target/manifest.json"))
            # for node_id, node in manifest["nodes"].items():
            #     if node["resource_type"] == "model":
            #         asset = self._model_to_asset(node)
            #         assets.append(asset)
            pass
        except Exception as e:
            print(f"Error fetching dbt assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific dbt model by ID."""
        # In production, parse manifest and find model
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from dbt DAG."""
        # In production, parse manifest["child_map"] and manifest["parent_map"]
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get schema from dbt catalog."""
        # In production, parse catalog.json
        return {"columns": []}

    def _model_to_asset(self, model: dict[str, Any]) -> Asset:
        """Convert dbt model to Asset."""
        return Asset(
            name=model.get("name", ""),
            description=model.get("description", ""),
            asset_type=AssetType.MODEL,
            platform="dbt",
            platform_id=model.get("unique_id", ""),
            domain=model.get("package_name", "default"),
            owner=model.get("meta", {}).get("owner"),
            tags=model.get("tags", []),
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "materialized": model.get("config", {}).get("materialized", "view"),
                "sql": model.get("raw_sql", ""),
                "path": model.get("path", ""),
                "package_name": model.get("package_name", ""),
            },
        )

    def get_models(self) -> list[Asset]:
        """Get all dbt models."""
        return self.get_assets()

    def get_sources(self) -> list[Asset]:
        """Get all dbt sources."""
        assets = []
        try:
            # In production, parse manifest["sources"]
            pass
        except Exception as e:
            print(f"Error fetching sources: {e}")
        return assets

    def get_snapshots(self) -> list[Asset]:
        """Get all dbt snapshots."""
        assets = []
        try:
            # In production, parse manifest for snapshots
            pass
        except Exception as e:
            print(f"Error fetching snapshots: {e}")
        return assets

    def get_seeds(self) -> list[Asset]:
        """Get all dbt seeds."""
        assets = []
        try:
            # In production, parse manifest for seeds
            pass
        except Exception as e:
            print(f"Error fetching seeds: {e}")
        return assets

    def get_tests(self) -> list[dict[str, Any]]:
        """Get all dbt tests."""
        tests = []
        try:
            # In production, parse manifest["tests"] and manifest["group_tests"]
            pass
        except Exception as e:
            print(f"Error fetching tests: {e}")
        return tests

    def get_exposures(self) -> list[dict[str, Any]]:
        """Get all dbt exposures."""
        exposures = []
        try:
            # In production, parse manifest["exposures"]
            pass
        except Exception as e:
            print(f"Error fetching exposures: {e}")
        return exposures

    def get_metrics(self) -> list[dict[str, Any]]:
        """Get all dbt metrics."""
        metrics = []
        try:
            # In production, parse manifest["metrics"]
            pass
        except Exception as e:
            print(f"Error fetching metrics: {e}")
        return metrics