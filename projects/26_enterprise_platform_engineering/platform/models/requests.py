"""
Request Models
Pydantic models for API request schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ServiceRequest(BaseModel):
    """Service creation/update request."""
    name: str = Field(..., min_length=3, max_length=100, description="Service name")
    category: str = Field(..., description="Service category")
    description: str = Field(..., description="Service description")
    version: str = Field(..., description="Service version")
    owner_team: str = Field(..., description="Owning team")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    api_endpoint: Optional[str] = Field(None, description="API endpoint URL")
    tags: List[str] = Field(default_factory=list, description="Service tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TemplateRequest(BaseModel):
    """Template rendering request."""
    template_id: str = Field(..., description="Template identifier")
    variables: Dict[str, Any] = Field(..., description="Template variables")


class ProvisioningRequest(BaseModel):
    """Provisioning request."""
    name: str = Field(..., min_length=3, max_length=100, description="Resource name")
    template_id: str = Field(..., description="Template to use")
    variables: Dict[str, Any] = Field(..., description="Template variables")
    environment: str = Field(..., description="Target environment")
    team: str = Field(..., description="Requesting team")


class ApprovalRequest(BaseModel):
    """Approval request."""
    comment: Optional[str] = Field(None, description="Approval/rejection comment")


class PolicyEvaluationRequest(BaseModel):
    """Policy evaluation request."""
    resource: Dict[str, Any] = Field(..., description="Resource to evaluate")
    policy_types: Optional[List[str]] = Field(None, description="Policy types to evaluate")