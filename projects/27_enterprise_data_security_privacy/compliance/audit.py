"""
Enterprise Audit Logging Service
Comprehensive audit trail and compliance logging
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_INCIDENT = "security_incident"
    PROVISIONING = "provisioning"
    COMPLIANCE = "compliance"


class AuditSeverity(str, Enum):
    """Audit event severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    actor: str
    actor_type: str
    resource: str
    resource_type: str
    action: str
    outcome: str
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    metadata: Dict[str, Any]


class AuditLogger:
    """
    Enterprise audit logging service
    Comprehensive audit trail for compliance
    """

    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self.events: List[AuditEvent] = []
        self.event_index: Dict[str, AuditEvent] = {}

    async def log_event(
        self,
        event_type: AuditEventType,
        actor: str,
        actor_type: str,
        resource: str,
        resource_type: str,
        action: str,
        outcome: str,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        ip_address: str = "",
        user_agent: str = "",
        details: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        """
        Log audit event

        Args:
            event_type: Type of event
            actor: Who performed action
            actor_type: Type of actor (user, service, system)
            resource: Resource affected
            resource_type: Type of resource
            action: Action performed
            outcome: Result (success, failure, denied)
            severity: Event severity
            ip_address: IP address
            user_agent: User agent
            details: Additional details
            metadata: Additional metadata

        Returns:
            Created audit event
        """
        event_id = f"audit-{datetime.utcnow().timestamp()}"

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            resource_type=resource_type,
            action=action,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            metadata=metadata or {}
        )

        # Store event
        self.events.append(event)
        self.event_index[event_id] = event

        logger.info(f"Audit event logged: {event_id}")

        return event

    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """
        Get audit event

        Args:
            event_id: Event identifier

        Returns:
            Audit event or None
        """
        return self.event_index.get(event_id)

    async def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        outcome: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit events

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            resource: Filter by resource
            start_time: Start time
            end_time: End time
            severity: Filter by severity
            outcome: Filter by outcome
            limit: Maximum results

        Returns:
            List of audit events
        """
        filtered = self.events

        # Apply filters
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        if actor:
            filtered = [e for e in filtered if e.actor == actor]

        if resource:
            filtered = [e for e in filtered if e.resource == resource]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        if outcome:
            filtered = [e for e in filtered if e.outcome == outcome]

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        return filtered[:limit]

    async def export_events(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> str:
        """
        Export audit events

        Args:
            start_time: Start time
            end_time: End time
            format: Export format

        Returns:
            Exported events
        """
        events = await self.query_events(start_time=start_time, end_time=end_time)

        if format == "json":
            return json.dumps([self._event_to_dict(e) for e in events], default=str)
        elif format == "csv":
            # Simplified CSV export
            lines = ["event_id,timestamp,event_type,actor,resource,action,outcome,severity"]
            for event in events:
                lines.append(
                    f"{event.event_id},{event.timestamp},{event.event_type.value},"
                    f"{event.actor},{event.resource},{event.action},{event.outcome},{event.severity.value}"
                )
            return "\n".join(lines)

        return ""

    def _event_to_dict(self, event: AuditEvent) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "timestamp": event.timestamp.isoformat(),
            "actor": event.actor,
            "actor_type": event.actor_type,
            "resource": event.resource,
            "resource_type": event.resource_type,
            "action": event.action,
            "outcome": event.outcome,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "details": event.details,
            "metadata": event.metadata
        }

    async def get_audit_trail(
        self,
        resource: str,
        limit: int = 50
    ) -> List[AuditEvent]:
        """
        Get audit trail for resource

        Args:
            resource: Resource identifier
            limit: Maximum results

        Returns:
            Audit trail
        """
        return await self.query_events(resource=resource, limit=limit)

    async def get_user_activity(
        self,
        actor: str,
        limit: int = 50
    ) -> List[AuditEvent]:
        """
        Get user activity

        Args:
            actor: User identifier
            limit: Maximum results

        Returns:
            User activity events
        """
        return await self.query_events(actor=actor, limit=limit)

    async def get_security_incidents(
        self,
        severity: AuditSeverity = AuditSeverity.HIGH
    ) -> List[AuditEvent]:
        """
        Get security incidents

        Args:
            severity: Minimum severity

        Returns:
            Security incidents
        """
        return await self.query_events(
            event_type=AuditEventType.SECURITY_INCIDENT,
            severity=severity
        )

    async def get_compliance_report(
        self,
        framework: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get compliance audit report

        Args:
            framework: Compliance framework
            start_time: Start time
            end_time: End time

        Returns:
            Compliance report
        """
        events = await self.query_events(
            event_type=AuditEventType.COMPLIANCE,
            start_time=start_time,
            end_time=end_time
        )

        report = {
            "framework": framework,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": len(events),
            "by_type": {},
            "by_severity": {},
            "by_outcome": {}
        }

        for event in events:
            # Count by type
            event_type = event.event_type.value
            report["by_type"][event_type] = report["by_type"].get(event_type, 0) + 1

            # Count by severity
            severity = event.severity.value
            report["by_severity"][severity] = report["by_severity"].get(severity, 0) + 1

            # Count by outcome
            report["by_outcome"][event.outcome] = report["by_outcome"].get(event.outcome, 0) + 1

        return report