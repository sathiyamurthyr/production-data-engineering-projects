"""Policy Models - Governance rule definitions."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Action(str, Enum):
    """Policy action types."""

    ALLOW = "allow"
    DENY = "deny"
    MASK = "mask"
    NOTIFY = "notify"
    QUARANTINE = "quarantine"


class SeverityLevel(str, Enum):
    """Policy severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Rule(BaseModel):
    """Individual policy rule."""

    condition: str
    action: Action
    remediation: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Policy(BaseModel):
    """Governance policy definition."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    type: str
    rules: list[Rule]
    severity: SeverityLevel = SeverityLevel.MEDIUM
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


class PolicyViolation(BaseModel):
    """Record of a policy violation."""

    policy_id: UUID
    asset_id: str
    rule_condition: str
    action_taken: Action
    timestamp: datetime = Field(default_factory=datetime.now)
    resolved: bool = False
    resolution: str | None = None