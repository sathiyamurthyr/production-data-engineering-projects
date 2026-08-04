"""
Audit Logger for Cross-Cloud Governance

This module provides comprehensive audit logging across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
from enum import Enum
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    POLICY_VIOLATION = "policy_violation"
    ACCESS_GRANT = "access_grant"
    ACCESS_REVOKE = "access_revoke"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"


class AuditEventSeverity(str, Enum):
    """Audit event severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event"""
    event_id: str
    event_type: AuditEventType
    severity: AuditEventSeverity
    timestamp: datetime
    user_id: str
    resource_id: str
    resource_type: str
    cloud: str
    action: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    request_id: str
    session_id: str
    result: str  # success, failure, partial
    error_message: Optional[str] = None


class AuditLogger:
    """
    Cross-cloud audit logger
    
    This service provides:
    - Comprehensive audit logging
    - Event correlation
    - Compliance reporting
    - Security monitoring
    """
    
    def __init__(self, config: Dict):
        """
        Initialize audit logger
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.events: Dict[str, AuditEvent] = {}
        self.event_index: Dict[str, List[str]] = {
            "user_id": [],
            "resource_id": [],
            "event_type": [],
            "cloud": []
        }
        
        # Configuration
        self.retention_days = config.get("retention_days", 365)
        self.max_events = config.get("max_events", 1000000)
        
        logger.info("Audit Logger initialized")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditEventSeverity,
        user_id: str,
        resource_id: str,
        resource_type: str,
        cloud: str,
        action: str,
        details: Dict[str, Any],
        ip_address: str,
        user_agent: str,
        request_id: str,
        session_id: str,
        result: str,
        error_message: Optional[str] = None
    ) -> AuditEvent:
        """
        Log audit event
        
        Args:
            event_type: Type of event
            severity: Event severity
            user_id: User ID
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            action: Action performed
            details: Event details
            ip_address: IP address
            user_agent: User agent
            request_id: Request ID
            session_id: Session ID
            result: Result (success, failure, partial)
            error_message: Error message if failed
            
        Returns:
            Audit event
        """
        logger.info(f"Logging audit event: {event_type.value}")
        
        # Generate event ID
        event_id = f"audit-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{request_id[:8]}"
        
        # Create event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            result=result,
            error_message=error_message
        )
        
        # Store event
        self.events[event_id] = event
        
        # Update indexes
        self._update_indexes(event)
        
        # Check if cleanup needed
        if len(self.events) > self.max_events:
            await self._cleanup_old_events()
        
        logger.info(f"Audit event logged: {event_id}")
        return event
    
    def _update_indexes(self, event: AuditEvent) -> None:
        """Update event indexes"""
        # User ID index
        if event.user_id not in self.event_index["user_id"]:
            self.event_index["user_id"].append(event.user_id)
        
        # Resource ID index
        if event.resource_id not in self.event_index["resource_id"]:
            self.event_index["resource_id"].append(event.resource_id)
        
        # Event type index
        if event.event_type.value not in self.event_index["event_type"]:
            self.event_index["event_type"].append(event.event_type.value)
        
        # Cloud index
        if event.cloud not in self.event_index["cloud"]:
            self.event_index["cloud"].append(event.cloud)
    
    async def _cleanup_old_events(self) -> None:
        """Cleanup old events"""
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Remove old events
        events_to_remove = []
        for event_id, event in self.events.items():
            if event.timestamp < cutoff_date:
                events_to_remove.append(event_id)
        
        for event_id in events_to_remove:
            del self.events[event_id]
        
        logger.info(f"Cleaned up {len(events_to_remove)} old audit events")
    
    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """
        Get audit event by ID
        
        Args:
            event_id: Event ID
            
        Returns:
            Audit event if found, None otherwise
        """
        return self.events.get(event_id)
    
    async def query_events(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        cloud: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """
        Query audit events
        
        Args:
            user_id: User ID (optional)
            resource_id: Resource ID (optional)
            event_type: Event type (optional)
            cloud: Cloud provider (optional)
            start_time: Start time (optional)
            end_time: End time (optional)
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of audit events
        """
        results = list(self.events.values())
        
        # Apply filters
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        
        if resource_id:
            results = [e for e in results if e.resource_id == resource_id]
        
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        
        if cloud:
            results = [e for e in results if e.cloud == cloud]
        
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        
        # Sort by timestamp desc
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]
    
    async def get_user_activity(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """
        Get user activity
        
        Args:
            user_id: User ID
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            List of audit events
        """
        # Default to last 30 days
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=30)
        
        return await self.query_events(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
    
    async def get_resource_history(
        self,
        resource_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """
        Get resource history
        
        Args:
            resource_id: Resource ID
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            List of audit events
        """
        # Default to last 30 days
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=30)
        
        return await self.query_events(
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
    
    async def get_security_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditEventSeverity] = None
    ) -> List[AuditEvent]:
        """
        Get security events
        
        Args:
            start_time: Start time (optional)
            end_time: End time (optional)
            severity: Severity filter (optional)
            
        Returns:
            List of security events
        """
        security_event_types = [
            AuditEventType.AUTHENTICATION,
            AuditEventType.AUTHORIZATION,
            AuditEventType.POLICY_VIOLATION,
            AuditEventType.ACCESS_GRANT,
            AuditEventType.ACCESS_REVOKE,
            AuditEventType.SECURITY_EVENT
        ]
        
        results = []
        for event_type in security_event_types:
            events = await self.query_events(
                event_type=event_type,
                start_time=start_time,
                end_time=end_time,
                limit=1000
            )
            results.extend(events)
        
        # Filter by severity
        if severity:
            results = [e for e in results if e.severity == severity]
        
        # Sort by timestamp desc
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results
    
    async def get_compliance_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get compliance report
        
        Args:
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            Compliance report
        """
        # Default to last 30 days
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=30)
        
        # Get all events in period
        events = await self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Calculate statistics
        total_events = len(events)
        
        # By event type
        by_type = {}
        for event in events:
            event_type = event.event_type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1
        
        # By severity
        by_severity = {}
        for event in events:
            severity = event.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # By cloud
        by_cloud = {}
        for event in events:
            cloud = event.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By result
        by_result = {}
        for event in events:
            result = event.result
            by_result[result] = by_result.get(result, 0) + 1
        
        # Failed events
        failed_events = [e for e in events if e.result == "failure"]
        
        # Security events
        security_events = [e for e in events if e.event_type in [
            AuditEventType.AUTHENTICATION,
            AuditEventType.AUTHORIZATION,
            AuditEventType.POLICY_VIOLATION,
            AuditEventType.SECURITY_EVENT
        ]]
        
        return {
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "total_events": total_events,
            "by_type": by_type,
            "by_severity": by_severity,
            "by_cloud": by_cloud,
            "by_result": by_result,
            "failed_events": len(failed_events),
            "security_events": len(security_events),
            "failed_event_details": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "user_id": e.user_id,
                    "action": e.action,
                    "error_message": e.error_message,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in failed_events[:100]
            ]
        }
    
    async def export_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json"
    ) -> str:
        """
        Export audit events
        
        Args:
            start_time: Start time (optional)
            end_time: End time (optional)
            format: Export format (json, csv)
            
        Returns:
            Exported events
        """
        # Get events
        events = await self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if format == "json":
            # Export as JSON
            event_dicts = []
            for event in events:
                event_dict = {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": event.user_id,
                    "resource_id": event.resource_id,
                    "resource_type": event.resource_type,
                    "cloud": event.cloud,
                    "action": event.action,
                    "details": event.details,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "request_id": event.request_id,
                    "session_id": event.session_id,
                    "result": event.result,
                    "error_message": event.error_message
                }
                event_dicts.append(event_dict)
            
            return json.dumps(event_dicts, indent=2)
        
        elif format == "csv":
            # Export as CSV
            lines = ["event_id,event_type,severity,timestamp,user_id,resource_id,cloud,action,result"]
            
            for event in events:
                line = (
                    f"{event.event_id},"
                    f"{event.event_type.value},"
                    f"{event.severity.value},"
                    f"{event.timestamp.isoformat()},"
                    f"{event.user_id},"
                    f"{event.resource_id},"
                    f"{event.cloud},"
                    f"{event.action},"
                    f"{event.result}"
                )
                lines.append(line)
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get audit analytics
        
        Returns:
            Audit statistics
        """
        total_events = len(self.events)
        
        # Recent events (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_events = [e for e in self.events.values() if e.timestamp >= cutoff]
        
        # By event type
        by_type = {}
        for event in self.events.values():
            event_type = event.event_type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1
        
        # By severity
        by_severity = {}
        for event in self.events.values():
            severity = event.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # By cloud
        by_cloud = {}
        for event in self.events.values():
            cloud = event.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # Failed events
        failed_events = [e for e in self.events.values() if e.result == "failure"]
        
        return {
            "total_events": total_events,
            "recent_events_24h": len(recent_events),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_cloud": by_cloud,
            "failed_events": len(failed_events),
            "failure_rate": (len(failed_events) / total_events * 100) if total_events > 0 else 0
        }