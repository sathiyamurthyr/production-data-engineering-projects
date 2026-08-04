"""Snowflake Connector - Snowflake metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class SnowflakeConnector(BaseConnector):
    """Harvest metadata from Snowflake."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Snowflake connector."""
        super().__init__(config)
        self.platform_name = "snowflake"
        self.account = config.get("account", "")
        self.user = config.get("user", "")
        self.password = config.get("password", "")
        self.warehouse = config.get("warehouse", "COMPUTE_WH")
        self.database = config.get("database", "")
        self.schema = config.get("schema", "")

    def test_connection(self) -> bool:
        """Test connection to Snowflake."""
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            conn.close()
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all tables from Snowflake."""
        assets = []
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            for row in cursor:
                asset = self._table_to_asset(row)
                assets.append(asset)
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching Snowflake assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific table by ID."""
        assets = self.get_assets()
        for asset in assets:
            if asset.platform_id == asset_id:
                return asset
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from Snowflake's ACCESS_HISTORY."""
        query = f"""
        SELECT 
            OBJECTS_REFERENCED,
            OBJECT_MODIFIED
        FROM {self.database}.INFORMATION_SCHEMA.ACCESS_HISTORY
        WHERE OBJECTS_REFERENCED LIKE '%{asset_id}%'
        """
        # Production implementation would parse query history
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get table schema from Snowflake."""
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            cursor = conn.cursor()
            cursor.execute(f"DESC TABLE {asset_id}")
            columns = []
            for row in cursor:
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "Y",
                    "default": row[4],
                    "primary_key": False,
                })
            cursor.close()
            conn.close()
            return {"columns": columns}
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {"columns": []}

    def _table_to_asset(self, row: tuple) -> Asset:
        """Convert Snowflake table row to Asset."""
        return Asset(
            name=row[1],
            description=f"Snowflake table in {self.database}.{self.schema}",
            asset_type=AssetType.TABLE,
            platform="snowflake",
            platform_id=f"{self.database}.{self.schema}.{row[1]}",
            domain=self.database,
            tags=["snowflake", self.schema],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "database": self.database,
                "schema": self.schema,
                "kind": row[2],
                "rows": row[5],
                "bytes": row[6],
            },
        )

    def get_views(self) -> list[Asset]:
        """Get all views from Snowflake."""
        assets = []
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW VIEWS")
            for row in cursor:
                asset = Asset(
                    name=row[1],
                    description=f"Snowflake view in {self.database}.{self.schema}",
                    asset_type=AssetType.VIEW,
                    platform="snowflake",
                    platform_id=f"{self.database}.{self.schema}.{row[1]}",
                    domain=self.database,
                    tags=["snowflake", "view", self.schema],
                    sensitivity=SensitivityLevel.INTERNAL,
                )
                assets.append(asset)
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching views: {e}")
        return assets

    def get_streams(self) -> list[Asset]:
        """Get all streams from Snowflake."""
        assets = []
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW STREAMS")
            for row in cursor:
                asset = Asset(
                    name=row[1],
                    description=f"Snowflake stream in {self.database}.{self.schema}",
                    asset_type=AssetType.STREAM,
                    platform="snowflake",
                    platform_id=f"{self.database}.{self.schema}.{row[1]}",
                    domain=self.database,
                    tags=["snowflake", "stream", self.schema],
                    sensitivity=SensitivityLevel.INTERNAL,
                )
                assets.append(asset)
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching streams: {e}")
        return assets

    def get_tasks(self) -> list[Asset]:
        """Get all tasks from Snowflake."""
        assets = []
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TASKS")
            for row in cursor:
                asset = Asset(
                    name=row[1],
                    description=f"Snowflake task in {self.database}.{self.schema}",
                    asset_type=AssetType.PIPELINE,
                    platform="snowflake",
                    platform_id=f"{self.database}.{self.schema}.{row[1]}",
                    domain=self.database,
                    tags=["snowflake", "task", self.schema],
                    sensitivity=SensitivityLevel.INTERNAL,
                )
                assets.append(asset)
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching tasks: {e}")
        return assets