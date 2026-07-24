"""Data models for Python Fundamentals project.

This module demonstrates Pydantic models for data validation
in data engineering pipelines.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class Customer(BaseModel):
    """Customer data model with validation.

    This demonstrates production-ready data modeling with validation
    for ETL pipelines.
    """

    customer_id: int = Field(..., gt=0, description="Unique customer identifier")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    signup_date: date
    country: str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., ge=0, le=120)

    @field_validator("country")
    @classmethod
    def normalize_country(cls, v: str) -> str:
        """Normalize country to uppercase."""
        return v.upper()

    @property
    def full_name(self) -> str:
        """Return customer's full name."""
        return f"{self.first_name} {self.last_name}"

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


class ETLJobConfig(BaseModel):
    """Configuration model for ETL jobs.

    Demonstrates configuration management with validation.
    """

    job_name: str = Field(..., min_length=1)
    source_table: str
    target_table: str
    batch_size: int = Field(default=1000, gt=0)
    incremental_column: Optional[str] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, gt=0)


class APIResponse(BaseModel):
    """Model for API response data with validation."""

    status_code: int = Field(ge=200, le=599)
    data: list[dict] | dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    model_config = {"str_strip_whitespace": True}