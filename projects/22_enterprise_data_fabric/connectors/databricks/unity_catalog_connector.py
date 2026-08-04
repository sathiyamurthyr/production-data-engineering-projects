"""Unity Catalog Connector - Databricks Unity Catalog metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class UnityCatalogConnector(BaseConnector):
    """Harvest metadata from Databricks Unity Catalog."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Unity Catalog connector."""
        super().__init__(config)
        self.platform_name = "unity_catalog"
        self.workspace_url = config.get("workspace_url", "")
        self.token = config.get("token", "")
        self.catalog = config.get("catalog", "main")

    def test_connection(self) -> bool:
        """Test connection to Unity Catalog."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            w.catalogs.get(self.catalog)
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all tables from Unity Catalog."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            
            schemas = w.schemas.list(catalog_name=self.catalog)
            for schema in schemas:
                tables = w.tables.list(catalog_name=self.catalog, schema_name=schema.name)
                for table in tables:
                    asset = self._table_to_asset(table, schema.name)
                    assets.append(asset)
        except Exception as e:
            print(f"Error fetching Unity Catalog assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific table by full name."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            parts = asset_id.split(".")
            if len(parts) == 3:
                catalog, schema, table = parts
                table_obj = w.tables.get(full_name=asset_id)
                return self._table_to_asset(table_obj, schema)
        except Exception as e:
            print(f"Error fetching asset {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from Unity Catalog."""
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            # Unity Catalog provides lineage through the lineage API
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

    def _table_to_asset(self, table: Any, schema_name: str) -> Asset:
        """Convert Unity Catalog table to Asset."""
        return Asset(
            name=table.name,
            description=table.comment or f"Unity Catalog table in {self.catalog}.{schema_name}",
            asset_type=AssetType.TABLE,
            platform="unity_catalog",
            platform_id=f"{self.catalog}.{schema_name}.{table.name}",
            domain=self.catalog,
            owner=table.owner,
            tags=["unity_catalog", self.catalog, schema_name],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "catalog": self.catalog,
                "schema": schema_name,
                "table_type": table.table_type,
                "data_source_format": table.data_source_format,
                "created_at": str(table.created_at) if hasattr(table, "created_at") else None,
                "updated_at": str(table.updated_at) if hasattr(table, "updated_at") else None,
            },
        )

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get all schemas in the catalog."""
        schemas = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            for schema in w.schemas.list(catalog_name=self.catalog):
                schemas.append({
                    "name": schema.name,
                    "full_name": schema.full_name,
                    "owner": schema.owner,
                    "comment": schema.comment,
                })
        except Exception as e:
            print(f"Error fetching schemas: {e}")
        return schemas

    def get_views(self) -> list[Asset]:
        """Get all views from Unity Catalog."""
        assets = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            schemas = w.schemas.list(catalog_name=self.catalog)
            for schema in schemas:
                tables = w.tables.list(catalog_name=self.catalog, schema_name=schema.name)
                for table in tables:
                    if hasattr(table, "view_definition") and table.view_definition:
                        asset = Asset(
                            name=table.name,
                            description=table.comment or f"Unity Catalog view",
                            asset_type=AssetType.VIEW,
                            platform="unity_catalog",
                            platform_id=f"{self.catalog}.{schema.name}.{table.name}",
                            domain=self.catalog,
                            owner=table.owner,
                            tags=["unity_catalog", "view", self.catalog, schema.name],
                            sensitivity=SensitivityLevel.INTERNAL,
                        )
                        assets.append(asset)
        except Exception as e:
            print(f"Error fetching views: {e}")
        return assets

    def get_volumes(self) -> list[dict[str, Any]]:
        """Get all volumes from Unity Catalog."""
        volumes = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            schemas = w.schemas.list(catalog_name=self.catalog)
            for schema in schemas:
                schema_volumes = w.volumes.list(catalog_name=self.catalog, schema_name=schema.name)
                for volume in schema_volumes:
                    volumes.append({
                        "name": volume.name,
                        "full_name": volume.full_name,
                        "volume_type": volume.volume_type,
                        "owner": volume.owner,
                        "comment": volume.comment,
                    })
        except Exception as e:
            print(f"Error fetching volumes: {e}")
        return volumes

    def get_functions(self) -> list[dict[str, Any]]:
        """Get all functions from Unity Catalog."""
        functions = []
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient(host=self.workspace_url, token=self.token)
            schemas = w.schemas.list(catalog_name=self.catalog)
            for schema in schemas:
                schema_functions = w.functions.list(catalog_name=self.catalog, schema_name=schema.name)
                for func in schema_functions:
                    functions.append({
                        "name": func.name,
                        "full_name": func.full_name,
                        "function_type": func.function_type,
                        "owner": func.owner,
                        "comment": func.comment,
                    })
        except Exception as e:
            print(f"Error fetching functions: {e}")
        return functions