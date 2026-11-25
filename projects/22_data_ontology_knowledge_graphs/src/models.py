"""Core dataclasses for Ontology schema, entity resolution, and knowledge graphs."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PropertySpec:
    """Schema constraint for an ontology class property."""

    name: str
    data_type: str
    required: bool = False
    allowed_values: Optional[List[str]] = None
    default: Any = None


@dataclass(frozen=True)
class ClassSpec:
    """Ontology Object Type definition with optional single-parent inheritance."""

    name: str
    description: str
    primary_key: str
    parent: Optional[str] = None
    abstract: bool = False
    properties: Dict[str, PropertySpec] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipSpec:
    """Ontology Link Type definition with domain, range, and reasoning flags."""

    name: str
    domain: str
    range: str
    cardinality: str = "N:M"
    inverse: Optional[str] = None
    transitive: bool = False
    description: str = ""


@dataclass(frozen=True)
class GraphNode:
    """Validated ontology instance stored in the Knowledge Graph."""

    uri: str
    class_name: str
    properties: Dict[str, Any]
    source_system: str = "unknown"


@dataclass(frozen=True)
class GraphEdge:
    """Validated semantic link between two Knowledge Graph nodes."""

    subject_uri: str
    predicate: str
    object_uri: str
    inferred: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedEntity:
    """Canonical entity produced by cross-source entity resolution."""

    canonical_uri: str
    canonical_id: str
    class_name: str
    properties: Dict[str, Any]
    source_ids: List[str]
    merge_confidence: float
