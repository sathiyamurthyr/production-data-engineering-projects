"""Enterprise Catalog - Central catalog service for data assets."""

from datetime import datetime
from typing import Any
from uuid import UUID

from ..metadata.models import Asset, AssetType, SensitivityLevel, Column
from ..metadata.repository import MetadataRepository


class CatalogService:
    """Enterprise catalog for asset registration and discovery."""

    def __init__(self, repository: MetadataRepository) -> None:
        """Initialize catalog service."""
        self.repository = repository
        self._assets: dict[str, Asset] = {}

    def register_asset(self, asset: Asset) -> Asset:
        """Register a new asset in the catalog."""
        asset.updated_at = datetime.now()
        self._assets[asset.urn] = asset
        self.repository.save_asset(asset)
        return asset

    def get_asset(self, urn: str) -> Asset | None:
        """Get asset by URN."""
        return self._assets.get(urn)

    def get_asset_by_id(self, asset_id: str) -> Asset | None:
        """Get asset by ID."""
        for asset in self._assets.values():
            if str(asset.id) == asset_id:
                return asset
        return None

    def update_asset(self, urn: str, updates: dict[str, Any]) -> Asset | None:
        """Update asset metadata."""
        asset = self._assets.get(urn)
        if not asset:
            return None
        for key, value in updates.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        asset.updated_at = datetime.now()
        self.repository.save_asset(asset)
        return asset

    def delete_asset(self, urn: str) -> bool:
        """Delete asset from catalog."""
        if urn in self._assets:
            del self._assets[urn]
            self.repository.delete_asset(urn)
            return True
        return False

    def list_assets(
        self,
        platform: str | None = None,
        domain: str | None = None,
        asset_type: AssetType | None = None,
        sensitivity: SensitivityLevel | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Asset]:
        """List assets with optional filters."""
        assets = list(self._assets.values())

        if platform:
            assets = [a for a in assets if a.platform == platform]
        if domain:
            assets = [a for a in assets if a.domain == domain]
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        if sensitivity:
            assets = [a for a in assets if a.sensitivity == sensitivity]
        if owner:
            assets = [a for a in assets if a.owner == owner]

        return assets[offset : offset + limit]

    def search_assets(self, query: str, limit: int = 50) -> list[Asset]:
        """Search assets by name or description."""
        query_lower = query.lower()
        results = []
        for asset in self._assets.values():
            if (
                query_lower in asset.name.lower()
                or (asset.description and query_lower in asset.description.lower())
            ):
                results.append(asset)
            elif any(query_lower in tag.lower() for tag in asset.tags):
                results.append(asset)
            elif any(query_lower in term.lower() for term in asset.glossary_terms):
                results.append(asset)
        return results[:limit]

    def get_asset_lineage(self, urn: str, depth: int = 3) -> dict[str, Any]:
        """Get lineage graph for an asset."""
        asset = self.get_asset(urn)
        if not asset:
            return {"nodes": [], "edges": []}

        nodes = [{"id": urn, "name": asset.name, "type": asset.asset_type.value}]
        edges = []

        for upstream_urn in asset.upstream_assets:
            upstream = self.get_asset(upstream_urn)
            if upstream:
                nodes.append(
                    {"id": upstream_urn, "name": upstream.name, "type": upstream.asset_type.value}
                )
                edges.append({"source": upstream_urn, "target": urn, "type": "LINEAGE"})

        for downstream_urn in asset.downstream_assets:
            downstream = self.get_asset(downstream_urn)
            if downstream:
                nodes.append(
                    {"id": downstream_urn, "name": downstream.name, "type": downstream.asset_type.value}
                )
                edges.append({"source": urn, "target": downstream_urn, "type": "LINEAGE"})

        return {"nodes": nodes, "edges": edges}

    def get_asset_dependencies(self, urn: str) -> dict[str, list[str]]:
        """Get upstream and downstream dependencies."""
        asset = self.get_asset(urn)
        if not asset:
            return {"upstream": [], "downstream": []}

        return {
            "upstream": asset.upstream_assets.copy(),
            "downstream": asset.downstream_assets.copy(),
        }

    def add_column(self, urn: str, column: Column) -> bool:
        """Add column to asset."""
        asset = self.get_asset(urn)
        if not asset:
            return False
        asset.columns.append(column)
        asset.updated_at = datetime.now()
        self.repository.save_asset(asset)
        return True

    def get_catalog_stats(self) -> dict[str, Any]:
        """Get catalog statistics."""
        assets = list(self._assets.values())
        return {
            "total_assets": len(assets),
            "by_type": self._count_by_field(assets, "asset_type"),
            "by_platform": self._count_by_field(assets, "platform"),
            "by_domain": self._count_by_field(assets, "domain"),
            "by_sensitivity": self._count_by_field(assets, "sensitivity"),
            "avg_quality_score": sum(a.quality_score for a in assets) / len(assets) if assets else 0,
        }

    def _count_by_field(self, assets: list[Asset], field: str) -> dict[str, int]:
        """Count assets by a specific field."""
        counts: dict[str, int] = {}
        for asset in assets:
            value = getattr(asset, field)
            if isinstance(value, Enum):
                value = value.value
            key = str(value) if value else "unknown"
            counts[key] = counts.get(key, 0) + 1
        return counts


# Import here to avoid circular imports
from enum import Enum