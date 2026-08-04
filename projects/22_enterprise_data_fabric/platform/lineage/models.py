"""Lineage Models - Data flow events and types."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LineageType(str, Enum):
    """Types of lineage relationships."""

    TRANSFORMATION = "transformation"
    COPY = "copy"
    STREAM = "stream"
    MERGE = "merge"


class LineageEvent(BaseModel):
    """Data lineage event."""

    id: UUID = Field(default_factory=uuid4)
    source_asset_id: str
    target_asset_id: str
    lineage_type: LineageType
    timestamp: datetime = Field(default_factory=datetime.now)
    job_id: str | None = None
    transformation_logic: str | None = None