"""Incident Manager - Comprehensive incident management for data platform."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels."""
    SEV1 = "sev1"  # Critical - Complete outage
    SEV2 = "sev2"  # High - Major degradation
    SEV3 = "sev3"  # Medium - Minor issues
    SEV4 = "sev4"  # Low - Cosmetic issues


class IncidentStatus(Enum):
    """Incident status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident(BaseModel):
    """Incident data model."""
    incident_id: str
    title: str
    description: str
    severity: str
    status: str
    source: str
    affected_services: list[str]
    assigned_to: str | None = None
    incident_commander: str | None = None
    started_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    root_cause: str | None = None
    remediation: str | None = None
    timeline: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}


class IncidentManager:
    """Manage incidents for the platform."""
    
    def __init__(self):
        """Initialize incident manager."""
        self.incidents: dict[str, Incident] = {}
        self.active_incidents: dict[str, Incident] = {}
        self.incident_history: list[Incident] = []
        self.response_times = {
            "sev1": timedelta(minutes=5),
            "sev2": timedelta(minutes=15),
            "sev3": timedelta(hours=1),
            "sev4": timedelta(hours=24),
        }
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: str,
        source: str,
        affected_services: list[str],
    ) -> Incident:
        """Create new incident.
        
        Args:
            title: Incident title
            description: Incident description
            severity: Severity level
            source: Alert source
            affected_services: Affected services
            
        Returns:
            Created incident
        """
        import uuid
        
        incident = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=title,
            description=description,
            severity=severity,
            status="open",
            source=source,
            affected_services=affected_services,
            started_at=datetime.now(),
            timeline=[{
                "timestamp": datetime.now().isoformat(),
                "event": "incident_created",
                "description": "Incident created",
            }],
        )
        
        self.incidents[incident.incident_id] = incident
        self.active_incidents[incident.incident_id] = incident
        
        logger.critical(f"Incident created: {incident.incident_id} - {title}")
        
        # Trigger notifications
        self._notify_incident_created(incident)
        
        return incident
    
    def acknowledge_incident(self, incident_id: str, acknowledged_by: str) -> bool:
        """Acknowledge incident.
        
        Args:
            incident_id: Incident identifier
            acknowledged_by: User acknowledging
            
        Returns:
            True if successful
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            return False
        
        incident.status = "acknowledged"
        incident.acknowledged_at = datetime.now()
        incident.assigned_to = acknowledged_by
        
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_acknowledged",
            "description": f"Acknowledged by {acknowledged_by}",
            "user": acknowledged_by,
        })
        
        logger.info(f"Incident acknowledged: {incident_id} by {acknowledged_by}")
        return True
    
    def update_status(self, incident_id: str, status: str, notes: str = None) -> bool:
        """Update incident status.
        
        Args:
            incident_id: Incident identifier
            status: New status
            notes: Update notes
            
        Returns:
            True if successful
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            return False
        
        old_status = incident.status
        incident.status = status
        
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "status_updated",
            "description": f"Status changed from {old_status} to {status}",
            "notes": notes,
        })
        
        logger.info(f"Incident {incident_id} status updated to {status}")
        return True
    
    def resolve_incident(
        self,
        incident_id: str,
        root_cause: str,
        remediation: str,
        resolved_by: str,
    ) -> bool:
        """Resolve incident.
        
        Args:
            incident_id: Incident identifier
            root_cause: Root cause analysis
            remediation: Remediation steps
            resolved_by: User resolving
            
        Returns:
            True if successful
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            return False
        
        incident.status = "resolved"
        incident.resolved_at = datetime.now()
        incident.root_cause = root_cause
        incident.remediation = remediation
        
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_resolved",
            "description": f"Resolved by {resolved_by}",
            "user": resolved_by,
            "root_cause": root_cause,
            "remediation": remediation,
        })
        
        # Move to history
        self.incident_history.append(incident)
        if incident_id in self.active_incidents:
            del self.active_incidents[incident_id]
        
        logger.info(f"Incident resolved: {incident_id}")
        
        # Trigger postmortem
        self._trigger_postmortem(incident)
        
        return True
    
    def get_active_incidents(self, severity: str = None) -> list[Incident]:
        """Get active incidents.
        
        Args:
            severity: Filter by severity
            
        Returns:
            List of active incidents
        """
        incidents = list(self.active_incidents.values())
        
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        
        return sorted(incidents, key=lambda i: i.started_at, reverse=True)
    
    def get_incident_summary(self) -> dict[str, Any]:
        """Get incident summary.
        
        Returns:
            Incident summary
        """
        active = list(self.active_incidents.values())
        
        return {
            "total_active": len(active),
            "by_severity": {
                "sev1": len([i for i in active if i.severity == "sev1"]),
                "sev2": len([i for i in active if i.severity == "sev2"]),
                "sev3": len([i for i in active if i.severity == "sev3"]),
                "sev4": len([i for i in active if i.severity == "sev4"]),
            },
            "by_service": self._count_by_service(active),
            "avg_resolution_time": self._calculate_avg_resolution_time(),
        }
    
    def _notify_incident_created(self, incident: Incident) -> None:
        """Notify on-call team of new incident.
        
        Args:
            incident: Incident
        """
        # Simplified - actual implementation would integrate with PagerDuty, Slack, etc.
        logger.info(f"Notifying on-call for incident {incident.incident_id}")
    
    def _trigger_postmortem(self, incident: Incident) -> None:
        """Trigger postmortem creation.
        
        Args:
            incident: Resolved incident
        """
        logger.info(f"Postmortem triggered for incident {incident.incident_id}")
    
    def _count_by_service(self, incidents: list[Incident]) -> dict[str, int]:
        """Count incidents by service.
        
        Args:
            incidents: List of incidents
            
        Returns:
            Count by service
        """
        counts = defaultdict(int)
        for incident in incidents:
            for service in incident.affected_services:
                counts[service] += 1
        
        return dict(counts)
    
    def _calculate_avg_resolution_time(self) -> timedelta:
        """Calculate average resolution time.
        
        Returns:
            Average resolution time
        """
        if not self.incident_history:
            return timedelta(0)
        
        total_time = timedelta(0)
        count = 0
        
        for incident in self.incident_history:
            if incident.resolved_at:
                resolution_time = incident.resolved_at - incident.started_at
                total_time += resolution_time
                count += 1
        
        if count == 0:
            return timedelta(0)
        
        return total_time / count


class IncidentTimeline:
    """Track incident timeline."""
    
    def __init__(self):
        """Initialize timeline."""
        self.events: list[dict[str, Any]] = []
    
    def add_event(
        self,
        incident_id: str,
        event_type: str,
        description: str,
        user: str = None,
        metadata: dict[str, Any] = None,
    ) -> None:
        """Add timeline event.
        
        Args:
            incident_id: Incident identifier
            event_type: Event type
            description: Event description
            user: User performing action
            metadata: Additional metadata
        """
        event = {
            "incident_id": incident_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "user": user,
            "metadata": metadata or {},
        }
        
        self.events.append(event)
    
    def get_timeline(self, incident_id: str) -> list[dict[str, Any]]:
        """Get incident timeline.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Timeline events
        """
        return [
            event for event in self.events
            if event["incident_id"] == incident_id
        ]


class PostmortemManager:
    """Manage incident postmortems."""
    
    def __init__(self):
        """Initialize postmortem manager."""
        self.postmortems: dict[str, dict[str, Any]] = {}
    
    def create_postmortem(
        self,
        incident_id: str,
        title: str,
        author: str,
    ) -> dict[str, Any]:
        """Create postmortem.
        
        Args:
            incident_id: Incident identifier
            title: Postmortem title
            author: Author
            
        Returns:
            Postmortem document
        """
        postmortem = {
            "incident_id": incident_id,
            "title": title,
            "author": author,
            "created_at": datetime.now().isoformat(),
            "status": "draft",
            "sections": {
                "summary": "",
                "timeline": [],
                "root_cause": "",
                "impact": "",
                "remediation": [],
                "preventive_measures": [],
                "lessons_learned": [],
            },
        }
        
        self.postmortems[incident_id] = postmortem
        return postmortem
    
    def update_section(
        self,
        incident_id: str,
        section: str,
        content: str,
    ) -> bool:
        """Update postmortem section.
        
        Args:
            incident_id: Incident identifier
            section: Section name
            content: Section content
            
        Returns:
            True if successful
        """
        postmortem = self.postmortems.get(incident_id)
        if not postmortem:
            return False
        
        if section not in postmortem["sections"]:
            return False
        
        postmortem["sections"][section] = content
        return True
    
    def finalize_postmortem(self, incident_id: str) -> dict[str, Any]:
        """Finalize postmortem.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Finalized postmortem
        """
        postmortem = self.postmortems.get(incident_id)
        if not postmortem:
            return {}
        
        postmortem["status"] = "finalized"
        postmortem["finalized_at"] = datetime.now().isoformat()
        
        return postmortem


class IncidentAnalyzer:
    """Analyze incidents for patterns."""
    
    def __init__(self):
        """Initialize incident analyzer."""
        self.incidents: list[Incident] = []
    
    def add_incident(self, incident: Incident) -> None:
        """Add incident for analysis.
        
        Args:
            incident: Incident
        """
        self.incidents.append(incident)
    
    def analyze_patterns(self) -> dict[str, Any]:
        """Analyze incident patterns.
        
        Returns:
            Analysis results
        """
        if not self.incidents:
            return {}
        
        # Group by service
        by_service = defaultdict(list)
        for incident in self.incidents:
            for service in incident.affected_services:
                by_service[service].append(incident)
        
        # Group by time
        by_hour = defaultdict(int)
        for incident in self.incidents:
            hour = incident.started_at.hour
            by_hour[hour] += 1
        
        # Find peak times
        peak_hours = sorted(by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "total_incidents": len(self.incidents),
            "by_service": {
                service: len(incidents)
                for service, incidents in by_service.items()
            },
            "by_severity": {
                "sev1": len([i for i in self.incidents if i.severity == "sev1"]),
                "sev2": len([i for i in self.incidents if i.severity == "sev2"]),
                "sev3": len([i for i in self.incidents if i.severity == "sev3"]),
                "sev4": len([i for i in self.incidents if i.severity == "sev4"]),
            },
            "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
            "avg_resolution_time": self._calculate_avg_resolution(),
        }
    
    def _calculate_avg_resolution(self) -> str:
        """Calculate average resolution time.
        
        Returns:
            Average resolution time string
        """
        resolved = [
            i for i in self.incidents
            if i.resolved_at
        ]
        
        if not resolved:
            return "N/A"
        
        total = sum(
            (i.resolved_at - i.started_at).total_seconds()
            for i in resolved
        )
        
        avg_seconds = total / len(resolved)
        avg_minutes = avg_seconds / 60
        
        return f"{avg_minutes:.1f} minutes"