"""Data Fabric Metadata Models - Asset and column definitions."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Types of data assets in the fabric."""

    TABLE = "table"
    VIEW = "view"
    STREAM = "stream"
    MODEL = "model"
    API = "api"
    REPORT = "report"
    DASHBOARD = "dashboard"
    PIPELINE = "pipeline"
    NOTEBOOK = "notebook"


class SensitivityLevel(str, Enum):
    """Data sensitivity classifications."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"
    PHI = "phi"


class Column(BaseModel):
    """Column definition with semantic mapping."""

    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    semantic_type: str | None = None
    business_term: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer_id",
                "data_type": "string",
                "nullable": False,
                "primary_key": True,
                "semantic_type": "identifier",
                "business_term": "Customer Identifier",
            }
        }


class Asset(BaseModel):
    """Data asset with rich metadata."""

    id: UUID = Field(default_factory=uuid4)
    urn: str  # Unique resource name
    name: str
    description: str | None = None
    asset_type: AssetType
    platform: str
    platform_id: str
    domain: str | None = None
    owner: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    columns: list[Column] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    quality_score: float = 1.0
    freshness: datetime | None = None
    upstream_assets: list[str] = Field(default_factory=list)
    downstream_assets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_search_document(self) -> dict[str, Any]:
        """Convert asset to search index document."""
        return {
            "id": str(self.id),
            "urn": self.urn,
            "name": self.name,
            "description": self.description,
            "asset_type": self.asset_type.value,
            "platform": self.platform,
            "domain": self.domain,
            "owner": self.owner,
            "tags": self.tags,
            "glossary_terms": self.glossary_terms,
            "sensitivity": self.sensitivity.value,
            "quality_score": self.quality_score,
        }