"""Metadata Repository - Store and query metadata assets."""

from typing import Any
from uuid import UUID

from pymongo import MongoClient
from pymongo.collection import Collection

from .models import Asset, AssetType, SensitivityLevel


class MetadataRepository:
    """Persistent storage for data assets."""

    def __init__(self, connection_string: str, database: str = "datafabric") -> None:
        """Initialize repository with MongoDB connection."""
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.assets: Collection = self.db.assets
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create database indexes for efficient queries."""
        self.assets.create_index("urn", unique=True)
        self.assets.create_index([("domain", 1), ("tags", 1)])
        self.assets.create_index([("platform", 1), ("sensitivity", 1)])

    def save(self, asset: Asset) -> Asset:
        """Save asset to repository."""
        self.assets.update_one(
            {"urn": asset.urn},
            {"$set": asset.model_dump()},
            upsert=True,
        )
        return asset

    def find_by_id(self, asset_id: UUID) -> Asset | None:
        """Find asset by ID."""
        doc = self.assets.find_one({"id": str(asset_id)})
        if doc:
            return Asset(**doc)
        return None

    def find_by_urn(self, urn: str) -> Asset | None:
        """Find asset by URN."""
        doc = self.assets.find_one({"urn": urn})
        if doc:
            return Asset(**doc)
        return None

    def search(
        self,
        query: str | None = None,
        asset_type: AssetType | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        sensitivity: SensitivityLevel | None = None,
    ) -> list[Asset]:
        """Search for assets matching criteria."""
        filter: dict[str, Any] = {}

        if query:
            filter["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
            ]
        if asset_type:
            filter["asset_type"] = asset_type.value
        if domain:
            filter["domain"] = domain
        if tags:
            filter["tags"] = {"$all": tags}
        if sensitivity:
            filter["sensitivity"] = sensitivity.value

        return [Asset(**doc) for doc in self.assets.find(filter)]

    def update_lineage(self, asset_id: UUID, upstream: list[str], downstream: list[str]) -> None:
        """Update lineage relationships for an asset."""
        self.assets.update_one(
            {"id": str(asset_id)},
            {"$set": {"upstream_assets": upstream, "downstream_assets": downstream}},
        )

    def get_domain_assets(self, domain: str) -> list[Asset]:
        """Get all assets for a domain."""
        return [Asset(**doc) for doc in self.assets.find({"domain": domain})]

    def get_stale_assets(self, older_than_days: int = 7) -> list[Asset]:
        """Get assets not updated recently."""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=older_than_days)
        return [
            Asset(**doc)
            for doc in self.assets.find({"updated_at": {"$lt": cutoff}})
        ]

    def close(self) -> None:
        """Close database connection."""
        self.client.close()