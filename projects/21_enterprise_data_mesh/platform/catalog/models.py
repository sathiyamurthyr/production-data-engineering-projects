"""Data Mesh Catalog Models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataClassification(str, Enum):
    """Data classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class SlaStatus(str, Enum):
    """SLA compliance status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    BREACH = "breach"


class ProductMetadata(BaseModel):
    """Metadata for a data product."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    domain: str
    owner: str
    created_at: datetime
    updated_at: datetime
    description: str
    classification: DataClassification
    tags: list[str] = Field(default_factory=list)
    documentation_url: str | None = None


class DataSchema(BaseModel):
    """Schema definition for a data product."""

    fields: list[dict[str, Any]]
    format: str = "delta"
    partition_by: list[str] | None = None
    clustering_by: list[str] | None = None


class SlaDefinition(BaseModel):
    """SLA definition for a data product."""

    freshness: str  # e.g., "24h"
    availability: float  # e.g., 99.9
    support_level: str  # e.g., "24x7"


class QualityCriteria(BaseModel):
    """Quality criteria for a data product."""

    completeness: float = 0.99
    uniqueness: float = 1.0
    validity: float = 0.99
    freshness_hours: int = 24


class DataProduct(BaseModel):
    """Data product model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    domain: str
    version: str
    owner: str
    description: str
    schema: DataSchema
    sla: SlaDefinition
    quality: QualityCriteria
    metadata: ProductMetadata
    status: str = "draft"  # draft, certified, deprecated, retired
    consumers: list[str] = Field(default_factory=list)

    @property
    def fully_qualified_name(self) -> str:
        """Return fully qualified product name."""
        return f"{self.domain}.{self.name}"

    @property
    def is_certified(self) -> bool:
        """Check if product is certified."""
        return self.status == "certified"


class ProductSearchResult(BaseModel):
    """Search result for data products."""

    products: list[DataProduct]
    total_count: int
    page: int
    page_size: int


class ProductHealth(BaseModel):
    """Health metrics for a data product."""

    freshness_status: SlaStatus
    quality_score: float
    availability: float
    last_updated: datetime
    next_update: datetime | None


class LineageInfo(BaseModel):
    """Lineage information for a data product."""

    upstream: list[str]  # parent product names
    downstream: list[str]  # child product names
    transformation_steps: list[str]
    last_lineage_update: datetime