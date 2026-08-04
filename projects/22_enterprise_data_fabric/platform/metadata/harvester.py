"""Metadata Harvester - Harvest metadata from various sources."""

import asyncio
from datetime import datetime
from typing import Any

from .models import Asset, AssetType, SensitivityLevel, Column


class MetadataHarvester:
    """Harvest metadata from all connected platforms."""

    def __init__(self, catalog: Any) -> None:
        """Initialize metadata harvester.
        
        Args:
            catalog: CatalogService instance to register assets
        """
        self.catalog = catalog
        self.connectors: dict[str, Any] = {}
        self.harvest_log: list[dict[str, Any]] = []

    def register_connector(self, name: str, connector: Any) -> None:
        """Register a metadata connector."""
        self.connectors[name] = connector

    async def harvest_all(self) -> dict[str, Any]:
        """Harvest metadata from all registered connectors."""
        results = {}
        for name, connector in self.connectors.items():
            try:
                assets = await self._harvest_connector(name, connector)
                results[name] = {
                    "status": "success",
                    "assets_harvested": len(assets),
                    "assets": assets,
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "assets_harvested": 0,
                }
        return results

    async def harvest_connector(self, name: str) -> dict[str, Any]:
        """Harvest metadata from a specific connector."""
        connector = self.connectors.get(name)
        if not connector:
            return {"status": "error", "error": f"Connector {name} not found"}
        
        try:
            assets = await self._harvest_connector(name, connector)
            return {
                "status": "success",
                "assets_harvested": len(assets),
                "assets": assets,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "assets_harvested": 0,
            }

    async def _harvest_connector(self, name: str, connector: Any) -> list[Asset]:
        """Harvest from a single connector."""
        assets = []
        
        # Test connection first
        if not connector.test_connection():
            raise ConnectionError(f"Failed to connect to {name}")

        # Get all assets
        connector_assets = connector.get_assets()
        
        for asset in connector_assets:
            # Enhance with additional metadata
            asset = self._enrich_asset(asset, connector)
            assets.append(asset)
            
            # Register in catalog
            self.catalog.register_asset(asset)
            
            # Log harvest
            self.harvest_log.append({
                "timestamp": datetime.now(),
                "connector": name,
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "action": "harvested",
            })

        return assets

    def _enrich_asset(self, asset: Asset, connector: Any) -> Asset:
        """Enrich asset with additional metadata."""
        # Get schema details
        try:
            schema = connector.get_schema(asset.platform_id)
            if schema and "columns" in schema:
                asset.columns = [
                    Column(
                        name=col["name"],
                        data_type=col.get("type", "unknown"),
                        nullable=col.get("nullable", True),
                        primary_key=col.get("primary_key", False),
                        description=col.get("description"),
                    )
                    for col in schema["columns"]
                ]
        except Exception as e:
            print(f"Warning: Could not enrich schema for {asset.name}: {e}")

        # Get lineage
        try:
            lineage = connector.get_lineage(asset.platform_id)
            if lineage and "edges" in lineage:
                for edge in lineage["edges"]:
                    if edge.get("source") not in asset.upstream_assets:
                        asset.upstream_assets.append(edge["source"])
                    if edge.get("target") not in asset.downstream_assets:
                        asset.downstream_assets.append(edge["target"])
        except Exception as e:
            print(f"Warning: Could not enrich lineage for {asset.name}: {e}")

        # Set freshness timestamp
        asset.freshness = datetime.now()

        return asset

    def get_harvest_stats(self) -> dict[str, Any]:
        """Get harvesting statistics."""
        total_assets = len(self.harvest_log)
        by_connector = {}
        for entry in self.harvest_log:
            connector = entry["connector"]
            by_connector[connector] = by_connector.get(connector, 0) + 1
        
        return {
            "total_assets_harvested": total_assets,
            "by_connector": by_connector,
            "connectors_registered": len(self.connectors),
            "last_harvest": self.harvest_log[-1]["timestamp"] if self.harvest_log else None,
        }

    def clear_harvest_log(self) -> None:
        """Clear harvest log."""
        self.harvest_log.clear()


class EventDrivenHarvester:
    """Event-driven metadata harvesting based on platform events."""

    def __init__(self, metadata_harvester: MetadataHarvester) -> None:
        """Initialize event-driven harvester."""
        self.metadata_harvester = metadata_harvester
        self.event_handlers: dict[str, list[Any]] = {}

    def register_handler(self, event_type: str, handler: Any) -> None:
        """Register event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def process_event(self, event: dict[str, Any]) -> None:
        """Process a metadata event."""
        event_type = event.get("type", "unknown")
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Error handling event {event_type}: {e}")

    async def handle_schema_change(self, event: dict[str, Any]) -> None:
        """Handle schema change event."""
        asset_id = event.get("asset_id")
        connector_name = event.get("connector")
        
        if connector_name in self.metadata_harvester.connectors:
            connector = self.metadata_harvester.connectors[connector_name]
            asset = connector.get_asset(asset_id)
            if asset:
                self.metadata_harvester.catalog.update_asset(
                    asset.urn,
                    {
                        "columns": asset.columns,
                        "updated_at": datetime.now(),
                    }
                )

    async def handle_new_asset(self, event: dict[str, Any]) -> None:
        """Handle new asset event."""
        connector_name = event.get("connector")
        asset_data = event.get("asset")
        
        if connector_name in self.metadata_harvester.connectors:
            connector = self.metadata_harvester.connectors[connector_name]
            asset = connector.to_asset(asset_data)
            self.metadata_harvester.catalog.register_asset(asset)