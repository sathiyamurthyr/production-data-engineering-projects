"""Semantic Layer Models - Business entities and metrics."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Granularity(str, Enum):
    """Metric granularity levels."""

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class Attribute(BaseModel):
    """Entity attribute with semantic mapping."""

    name: str
    semantic_type: str
    source_columns: list[dict[str, Any]] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)


class SemanticEntity(BaseModel):
    """Business entity in semantic layer."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    domain: str
    owners: list[str] = Field(default_factory=list)
    attributes: list[Attribute] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


class SemanticMetric(BaseModel):
    """Business metric definition."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    calculation: str
    dimensions: list[str] = Field(default_factory=list)
    granularity: Granularity
    owners: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"