"""Lineage Tracker - Capture and process data lineage events."""

from typing import Any

from .models import LineageEvent, LineageType


class LineageTracker:
    """Track data lineage across platforms."""

    def __init__(self) -> None:
        """Initialize lineage tracker."""
        self.events: list[LineageEvent] = []

    def capture_lineage(self, event: LineageEvent) -> None:
        """Capture a lineage event."""
        self.events.append(event)

    def get_lineage_for_asset(self, asset_id: str) -> list[LineageEvent]:
        """Get all lineage events for an asset."""
        return [
            e for e in self.events
            if e.source_asset_id == asset_id or e.target_asset_id == asset_id
        ]

    def get_downstream_assets(self, asset_id: str) -> list[str]:
        """Get all downstream assets from an asset."""
        return list({
            e.target_asset_id
            for e in self.events
            if e.source_asset_id == asset_id
        })

    def get_upstream_assets(self, asset_id: str) -> list[str]:
        """Get all upstream assets to an asset."""
        return list({
            e.source_asset_id
            for e in self.events
            if e.target_asset_id == asset_id
        })

    def build_lineage_graph(self) -> dict[str, Any]:
        """Build lineage graph structure."""
        return {
            "nodes": [],
            "edges": [],
        }