"""
Audit Logger Module
===================
Provides immutable audit trail recording for all data access requests, policy
evaluations, permission checks, and security violation attempts.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class AuditEvent:
    """Represents a single audited security or access event."""
    user_id: str
    action: str  # "READ", "QUERY", "EXPORT", "PERMISSION_GRANT"
    asset_id: str
    decision: str  # "ALLOW", "MASK", "DENY"
    details: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return asdict(self)


class AuditLogger:
    """
    Central audit log repository supporting append-only logging and compliance queries.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def log_access(
        self,
        user_id: str,
        action: str,
        asset_id: str,
        decision: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Record a new access request event to the audit log.
        
        Args:
            user_id: User attempting action.
            action: Action requested (READ, WRITE, QUERY, etc.).
            asset_id: Target asset or column identifier.
            decision: Policy decision (ALLOW, MASK, DENY).
            details: Optional metadata context dictionary.
            
        Returns:
            Recorded AuditEvent instance.
        """
        event = AuditEvent(
            user_id=user_id,
            action=action,
            asset_id=asset_id,
            decision=decision,
            details=details or {},
        )
        self._events.append(event)
        
        log_msg = f"AUDIT [{event.decision}] user='{user_id}' action='{action}' asset='{asset_id}'"
        if decision == "DENY":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return event

    def get_events_by_user(self, user_id: str) -> List[AuditEvent]:
        """Retrieve audit history for a specific user."""
        return [e for e in self._events if e.user_id == user_id]

    def get_unauthorized_attempts(self) -> List[AuditEvent]:
        """Retrieve all DENIED access attempts for security investigation."""
        return [e for e in self._events if e.decision == "DENY"]

    def export_json(self) -> str:
        """Export full audit log history to JSON string."""
        return json.dumps([e.to_dict() for e in self._events], indent=2)

    def total_events_count(self) -> int:
        """Return total count of recorded audit events."""
        return len(self._events)
