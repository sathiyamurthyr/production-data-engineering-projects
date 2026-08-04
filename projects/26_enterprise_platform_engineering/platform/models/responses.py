"""
Response Models
Pydantic models for API response schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, Dict[str, str]] = Field(..., description="Service health status")


class ServiceResponse(BaseModel):
    """Service response model."""
    id: str = Field(..., description="Service ID")
    name: str = Field(..., description="Service name")
    category: str = Field(..., description="Service category")
    description: str = Field(..., description="Service description")
    version: str = Field(..., description="Service version")
    owner_team: str = Field(..., description="Owning team")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    api_endpoint: Optional[str] = Field(None, description="API endpoint")
    status: str = Field(..., description="Service status")
    tags: List[str] = Field(..., description="Service tags")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class TemplateResponse(BaseModel):
    """Template response model."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    category: str = Field(..., description="Template category")
    description: str = Field(..., description="Template description")
    version: str = Field(..., description="Template version")
    author: str = Field(..., description="Template author")
    tags: List[str] = Field(..., description="Template tags")
    schema: Dict[str, Any] = Field(..., description="Variable schema")
    status: str = Field(..., description="Template status")
    downloads: int = Field(..., description="Download count")
    rating: int = Field(..., description="Template rating")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ProvisioningResponse(BaseModel):
    """Provisioning response model."""
    provisioning_id: Optional[str] = Field(None, description="Provisioning request ID")
    status: str = Field(..., description="Provisioning status")
    approval_id: Optional[str] = Field(None, description="Approval request ID if approval needed")
    message: str = Field(..., description="Status message")
    estimated_time: Optional[int] = Field(None, description="Estimated time in seconds")
    created_at: str = Field(..., description="Creation timestamp")


class ApprovalResponse(BaseModel):
    """Approval response model."""
    id: str = Field(..., description="Approval ID")
    provisioning_id: str = Field(..., description="Associated provisioning ID")
    status: str = Field(..., description="Approval status")
    requested_from: str = Field(..., description="Approver")
    requested_by: str = Field(..., description="Requester")
    comment: Optional[str] = Field(None, description="Comment")
    approved_at: Optional[str] = Field(None, description="Approval timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")
    created_at: str = Field(..., description="Creation timestamp")


class PolicyResponse(BaseModel):
    """Policy response model."""
    id: str = Field(..., description="Policy ID")
    name: str = Field(..., description="Policy name")
    policy_type: str = Field(..., description="Policy type")
    severity: str = Field(..., description="Policy severity")
    description: str = Field(..., description="Policy description")
    enabled: bool = Field(..., description="Whether policy is enabled")
    tags: List[str] = Field(..., description="Policy tags")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class PolicyViolationResponse(BaseModel):
    """Policy violation response model."""
    id: str = Field(..., description="Violation ID")
    policy_id: str = Field(..., description="Policy ID")
    resource_id: str = Field(..., description="Resource ID")
    resource_type: str = Field(..., description="Resource type")
    severity: str = Field(..., description="Violation severity")
    message: str = Field(..., description="Violation message")
    remediation: Optional[str] = Field(None, description="Remediation steps")
    resolved: bool = Field(..., description="Whether violation is resolved")
    created_at: str = Field(..., description="Creation timestamp")


class StatisticsResponse(BaseModel):
    """Statistics response model."""
    total_services: int = Field(..., description="Total number of services")
    active_services: int = Field(..., description="Number of active services")
    total_templates: int = Field(..., description="Total number of templates")
    total_provisions: int = Field(..., description="Total provisioning requests")
    pending_provisions: int = Field(..., description="Pending provisioning requests")
    completed_provisions: int = Field(..., description="Completed provisioning requests")
    total_policies: int = Field(..., description="Total policies")
    policy_violations: int = Field(..., description="Total policy violations")
    timestamp: str = Field(..., description="Statistics timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Offset from start")
    has_more: bool = Field(..., description="Whether there are more items")