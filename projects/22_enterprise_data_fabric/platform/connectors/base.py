"""Base connector interface for all platform connectors."""

from abc import ABC, abstractmethod
from typing import Any

from ..metadata.models import Asset, AssetType


class BaseConnector(ABC):
    """Base class for all data platform connectors."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize connector with configuration."""
        self.config = config
        self.platform_name = "base"

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the platform."""
        raise NotImplementedError

    @abstractmethod
    def get_assets(self) -> list[Asset]:
        """Retrieve all assets from the platform."""
        raise NotImplementedError

    @abstractmethod
    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific asset by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage for an asset."""
        raise NotImplementedError

    @abstractmethod
    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get schema details for an asset."""
        raise NotImplementedError

    def to_asset(self, raw_asset: dict[str, Any]) -> Asset:
        """Convert platform-specific asset to common Asset model."""
        return Asset(
            name=raw_asset.get("name", ""),
            description=raw_asset.get("description"),
            asset_type=AssetType(raw_asset.get("type", "table")),
            platform=self.platform_name,
            platform_id=raw_asset.get("id", ""),
            domain=raw_asset.get("domain"),
            owner=raw_asset.get("owner"),
            tags=raw_asset.get("tags", []),
            sensitivity=raw_asset.get("sensitivity", "internal"),
            metadata=raw_asset.get("metadata", {}),
        )