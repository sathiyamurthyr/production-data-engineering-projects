"""Semantic Query - Business-friendly query interface."""

from typing import Any

from .models import SemanticEntity, SemanticMetric


class SemanticQuery:
    """Business-friendly query interface."""

    def __init__(self, metadata_repo, graph_instance) -> None:
        """Initialize with metadata repository and graph."""
        self.metadata = metadata_repo
        self.graph = graph_instance

    def query_entity(self, entity_name: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Query using business entity name."""
        # Resolve entity to physical assets
        # Apply transformations
        # Return results
        pass

    def query_metric(
        self,
        metric_name: str,
        dimensions: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query using business metric."""
        # Resolve metric calculation
        # Apply filters and dimensions
        # Return aggregated results
        pass

    def list_entities(self, domain: str | None = None) -> list[SemanticEntity]:
        """List available semantic entities."""
        pass

    def list_metrics(self, domain: str | None = None) -> list[SemanticMetric]:
        """List available metrics."""
        pass