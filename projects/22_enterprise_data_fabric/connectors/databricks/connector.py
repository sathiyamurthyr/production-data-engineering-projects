"""Databricks Connector - Databricks metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class DatabricksConnector(BaseConnector):
    """Harvest metadata from Databricks."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Databricks connector."""
        super().__init__(config)
        self.platform_name = "databricks"
        self.workspace_url = config.get("workspace_url", "")
        self.token = config.get("token", "")
        self.catalog = config.get("catalog", "main")
        self.schema = config.get("schema", "default")

    def test_connection(self) -> bool:
        """Test connection to Databricks."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            w.current_user.me()
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all tables from Databricks Unity Catalog."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            tables = w.tables.list(catalog_name=self.catalog, schema_name=self.schema)
            for table in tables:
                asset = self._table_to_asset(table)
                assets.append(asset)
        except Exception as e:
            print(f"Error fetching Databricks assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific table by ID."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            parts = asset_id.split(".")
            if len(parts) == 3:
                catalog, schema, table = parts
                table_obj = w.tables.get(full_name=asset_id)
                return self._table_to_asset(table_obj)
        except Exception as e:
            print(f"Error fetching asset {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from Unity Catalog."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            lineage = w.lineage.get(asset_id)
            return {
                "nodes": [{"id": asset_id, "name": asset_id}],
                "edges": [],
            }
        except Exception as e:
            print(f"Error fetching lineage: {e}")
            return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get table schema from Unity Catalog."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            table = w.tables.get(full_name=asset_id)
            columns = []
            for col in table.columns:
                columns.append({
                    "name": col.name,
                    "type": col.data_type,
                    "nullable": col.nullable,
                    "primary_key": col.primary_key,
                    "description": col.comment,
                })
            return {"columns": columns}
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {"columns": []}

    def _table_to_asset(self, table: Any) -> Asset:
        """Convert Databricks table to Asset."""
        return Asset(
            name=table.name,
            description=table.comment or f"Databricks table in {self.catalog}.{self.schema}",
            asset_type=AssetType.TABLE,
            platform="databricks",
            platform_id=f"{self.catalog}.{self.schema}.{table.name}",
            domain=self.catalog,
            owner=table.owner,
            tags=["databricks", self.catalog, self.schema],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "catalog": self.catalog,
                "schema": self.schema,
                "table_type": table.table_type,
                "data_source_format": table.data_source_format,
            },
        )

    def get_views(self) -> list[Asset]:
        """Get all views from Databricks."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            tables = w.tables.list(catalog_name=self.catalog, schema_name=self.schema)
            for table in tables:
                if hasattr(table, 'view_definition') and table.view_definition:
                    asset = Asset(
                        name=table.name,
                        description=table.comment or f"Databricks view",
                        asset_type=AssetType.VIEW,
                        platform="databricks",
                        platform_id=f"{self.catalog}.{self.schema}.{table.name}",
                        domain=self.catalog,
                        owner=table.owner,
                        tags=["databricks", "view", self.catalog, self.schema],
                        sensitivity=SensitivityLevel.INTERNAL,
                    )
                    assets.append(asset)
        except Exception as e:
            print(f"Error fetching views: {e}")
        return assets

    def get_models(self) -> list[Asset]:
        """Get MLflow models from Databricks."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            models = w.mlflow_models.list()
            for model in models:
                asset = Asset(
                    name=model.name,
                    description=f"MLflow model: {model.description}",
                    asset_type=AssetType.MODEL,
                    platform="databricks",
                    platform_id=model.name,
                    domain=self.catalog,
                    owner=model.user_id,
                    tags=["databricks", "mlflow", "model"],
                    sensitivity=SensitivityLevel.INTERNAL,
                )
                assets.append(asset)
        except Exception as e:
            print(f"Error fetching models: {e}")
        return assets

    def get_notebooks(self, path: str = "/") -> list[Asset]:
        """Get notebooks from Databricks workspace."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            notebooks = w.workspace.list(path=path)
            for nb in notebooks:
                asset = Asset(
                    name=nb.path.split("/")[-1],
                    description=f"Databricks notebook at {nb.path}",
                    asset_type=AssetType.NOTEBOOK,
                    platform="databricks",
                    platform_id=nb.path,
                    domain=self.catalog,
                    tags=["databricks", "notebook"],
                    sensitivity=SensitivityLevel.INTERNAL,
                )
                assets.append(asset)
        except Exception as e:
            print(f"Error fetching notebooks: {e}")
        return assets