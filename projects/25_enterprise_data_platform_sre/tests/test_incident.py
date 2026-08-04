"""Tests for incident management."""

import pytest
from datetime import datetime, timedelta

from incident.manager import (
    IncidentManager,
    IncidentSeverity,
    IncidentStatus,
    IncidentTimeline,
    PostmortemManager,
    IncidentAnalyzer,
)


class TestIncidentManager:
    """Test incident manager."""
    
    def test_create_incident(self):
        """Test creating incident."""
        manager = IncidentManager()
        
        incident = manager.create_incident(
            title="Test Incident",
            description="Test description",
            severity="sev2",
            source="monitoring",
            affected_services=["service-1", "service-2"],
        )
        
        assert incident.incident_id is not None
        assert incident.title == "Test Incident"
        assert incident.severity == "sev2"
        assert incident.status == "open"
        assert len(incident.affected_services) == 2
        assert incident.incident_id in manager.active_incidents
    
    def test_acknowledge_incident(self):
        """Test acknowledging incident."""
        manager = IncidentManager()
        
        incident = manager.create_incident(
            title="Test",
            description="Test",
            severity="sev2",
            source="test",
            affected_services=["service-1"],
        )
        
        result = manager.acknowledge_incident(incident.incident_id, "john.doe")
        
        assert result is True
        assert incident.status == "acknowledged"
        assert incident.acknowledged_by == "john.doe"
        assert incident.acknowledged_at is not None
    
    def test_acknowledge_nonexistent_incident(self):
        """Test acknowledging non-existent incident."""
        manager = IncidentManager()
        
        result = manager.acknowledge_incident("INC-NONEXISTENT", "john.doe")
        
        assert result is False
    
    def test_update_status(self):
        """Test updating incident status."""
        manager = IncidentManager()
        
        incident = manager.create_incident(
            title="Test",
            description="Test",
            severity="sev2",
            source="test",
            affected_services=["service-1"],
        )
        
        result = manager.update_status(incident.incident_id, "investigating", "Looking into it")
        
        assert result is True
        assert incident.status == "investigating"
        assert len(incident.timeline) == 2  # Initial + update
    
    def test_resolve_incident(self):
        """Test resolving incident."""
        manager = IncidentManager()
        
        incident = manager.create_incident(
            title="Test",
            description="Test",
            severity="sev2",
            source="test",
            affected_services=["service-1"],
        )
        
        result = manager.resolve_incident(
            incident_id=incident.incident_id,
            root_cause="Database connection pool exhaustion",
            remediation="Increased connection pool size",
            resolved_by="jane.doe",
        )
        
        assert result is True
        assert incident.status == "resolved"
        assert incident.root_cause == "Database connection pool exhaustion"
        assert incident.resolved_at is not None
        assert incident.incident_id not in manager.active_incidents
        assert incident.incident_id in [i.incident_id for i in manager.incident_history]
    
    def test_get_active_incidents(self):
        """Test getting active incidents."""
        manager = IncidentManager()
        
        # Create multiple incidents
        inc1 = manager.create_incident("Incident 1", "Desc", "sev1", "test", ["svc1"])
        inc2 = manager.create_incident("Incident 2", "Desc", "sev2", "test", ["svc2"])
        inc3 = manager.create_incident("Incident 3", "Desc", "sev3", "test", ["svc3"])
        
        # Resolve one
        manager.resolve_incident(inc3.incident_id, "Root cause", "Fix", "user")
        
        # Get all active
        active = manager.get_active_incidents()
        assert len(active) == 2
        
        # Get by severity
        sev1_incidents = manager.get_active_incidents(severity="sev1")
        assert len(sev1_incidents) == 1
        assert sev1_incidents[0].incident_id == inc1.incident_id
    
    def test_get_incident_summary(self):
        """Test getting incident summary."""
        manager = IncidentManager()
        
        manager.create_incident("Incident 1", "Desc", "sev1", "test", ["svc1", "svc2"])
        manager.create_incident("Incident 2", "Desc", "sev2", "test", ["svc2"])
        
        summary = manager.get_incident_summary()
        
        assert summary["total_active"] == 2
        assert summary["by_severity"]["sev1"] == 1
        assert summary["by_severity"]["sev2"] == 1
        assert summary["by_service"]["svc2"] == 2


class TestIncidentTimeline:
    """Test incident timeline."""
    
    def test_add_event(self):
        """Test adding timeline event."""
        timeline = IncidentTimeline()
        
        timeline.add_event(
            incident_id="INC-001",
            event_type="status_change",
            description="Status changed to investigating",
            user="john.doe",
            metadata={"old_status": "open", "new_status": "investigating"},
        )
        
        events = timeline.get_timeline("INC-001")
        assert len(events) == 1
        assert events[0]["event_type"] == "status_change"
        assert events[0]["user"] == "john.doe"
    
    def test_get_timeline_empty(self):
        """Test getting timeline for non-existent incident."""
        timeline = IncidentTimeline()
        
        events = timeline.get_timeline("INC-NONEXISTENT")
        assert len(events) == 0


class TestPostmortemManager:
    """Test postmortem manager."""
    
    def test_create_postmortem(self):
        """Test creating postmortem."""
        manager = PostmortemManager()
        
        postmortem = manager.create_postmortem(
            incident_id="INC-001",
            title="Database Outage Postmortem",
            author="john.doe",
        )
        
        assert postmortem["incident_id"] == "INC-001"
        assert postmortem["title"] == "Database Outage Postmortem"
        assert postmortem["status"] == "draft"
        assert "summary" in postmortem["sections"]
    
    def test_update_section(self):
        """Test updating postmortem section."""
        manager = PostmortemManager()
        
        manager.create_postmortem("INC-001", "Test", "john.doe")
        result = manager.update_section("INC-001", "summary", "Database outage due to...")
        
        assert result is True
        assert manager.postmortems["INC-001"]["sections"]["summary"] == "Database outage due to..."
    
    def test_update_nonexistent_section(self):
        """Test updating non-existent section."""
        manager = PostmortemManager()
        
        manager.create_postmortem("INC-001", "Test", "john.doe")
        result = manager.update_section("INC-001", "nonexistent", "content")
        
        assert result is False
    
    def test_finalize_postmortem(self):
        """Test finalizing postmortem."""
        manager = PostmortemManager()
        
        manager.create_postmortem("INC-001", "Test", "john.doe")
        postmortem = manager.finalize_postmortem("INC-001")
        
        assert postmortem["status"] == "finalized"
        assert "finalized_at" in postmortem


class TestIncidentAnalyzer:
    """Test incident analyzer."""
    
    def test_analyze_patterns_empty(self):
        """Test analyzing patterns with no incidents."""
        analyzer = IncidentAnalyzer()
        
        result = analyzer.analyze_patterns()
        
        assert result == {}
    
    def test_analyze_patterns(self):
        """Test analyzing incident patterns."""
        analyzer = IncidentAnalyzer()
        
        # Add some incidents
        analyzer.add_incident(self._create_test_incident("sev1", ["svc1", "svc2"]))
        analyzer.add_incident(self._create_test_incident("sev2", ["svc1"]))
        analyzer.add_incident(self._create_test_incident("sev1", ["svc2"]))
        
        result = analyzer.analyze_patterns()
        
        assert result["total_incidents"] == 3
        assert result["by_severity"]["sev1"] == 2
        assert result["by_severity"]["sev2"] == 1
        assert result["by_service"]["svc1"] == 2
        assert result["by_service"]["svc2"] == 2
    
    def _create_test_incident(self, severity: str, services: list[str]):
        """Create test incident."""
        from unittest.mock import Mock
        
        incident = Mock()
        incident.severity = severity
        incident.affected_services = services
        incident.started_at = datetime.now()
        incident.resolved_at = datetime.now() + timedelta(minutes=30)
        
        return incident