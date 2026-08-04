"""Knowledge Graph Models - Nodes and relationships."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""

    ASSET = "asset"
    COLUMN = "column"
    TERM = "term"
    OWNER = "owner"
    DOMAIN = "domain"
    METRIC = "metric"


class GraphNode(BaseModel):
    """Node in the knowledge graph."""

    id: UUID
    entity_type: EntityType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)

    def to_neo4j_dict(self) -> dict[str, Any]:
        """Convert to Neo4j node format."""
        return {
            "id": str(self.id),
            "labels": [self.entity_type.value] + self.labels,
            "properties": {"name": self.name, **self.properties},
        }


class GraphRelationship(BaseModel):
    """Relationship between graph nodes."""

    id: UUID
    type: str
    source_id: UUID
    target_id: UUID
    properties: dict[str, Any] = Field(default_factory=dict)

    def to_neo4j_dict(self) -> dict[str, Any]:
        """Convert to Neo4j relationship format."""
        return {
            "id": str(self.id),
            "type": self.type,
            "start_node_id": str(self.source_id),
            "end_node_id": str(self.target_id),
            "properties": self.properties,
        }