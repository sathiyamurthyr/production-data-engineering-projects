"""Business Glossary Models - Terms and categories."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Category(BaseModel):
    """Glossary category for organizing terms."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    parent_id: UUID | None = None
    children: list[UUID] = Field(default_factory=list)


class Term(BaseModel):
    """Business term definition."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    definition: str
    category_id: UUID | None = None
    synonyms: list[str] = Field(default_factory=list)
    related_terms: list[UUID] = Field(default_factory=list)
    stewards: list[str] = Field(default_factory=list)
    mapped_columns: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Customer Lifetime Value",
                "definition": "Total revenue expected from a customer over their relationship",
                "category": "Revenue Metrics",
                "synonyms": ["CLV", "Customer Value"],
            }
        }