"""Alert Manager - Comprehensive alert management for data platform."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Alert(BaseModel):
    """Alert data model."""
    alert_id: str
    severity: str  # critical, warning, info
    status: str  # firing, acknowledged, resolved
    title: str
    description: str
    source: str
    labels: dict[str, str]
    annotations: dict[str, str]
    started_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    runbook_url: str | None = None


class AlertRule(BaseModel):
    """Alert rule definition."""
    rule_id: str
    name: str
    description: str
    expression: str  # PromQL or other query
    severity: str
    duration: int  # Duration in seconds
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    runbook_url: str | None = None


class AlertManager:
    """Manage alerts for the platform."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.alerts: dict[str, Alert] = {}
        self.rules: dict[str, AlertRule] = {}
        self.alert_history: list[Alert] = []
        self.deduplication_window = timedelta(minutes=5)
        self.active_alerts: dict[str, Alert] = {}
    
    def register_rule(self, rule: AlertRule) -> None:
        """Register alert rule.
        
        Args:
            rule: Alert rule definition
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered alert rule: {rule.name}")
    
    def evaluate_alert(self, rule_id: str, current_value: float) -> Alert | None:
        """Evaluate alert rule against current value.
        
        Args:
            rule_id: Rule identifier
            current_value: Current metric value
            
        Returns:
            Alert if triggered, None otherwise
        """
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        
        # Check if threshold breached
        if current_value > self._extract_threshold(rule.expression):
            alert = self._create_alert(rule, current_value)
            
            # Deduplication
            if not self._is_duplicate(alert):
                self.alerts[alert.alert_id] = alert
                self.active_alerts[alert.alert_id] = alert
                logger.warning(f"Alert triggered: {alert.title}")
                return alert
        
        return None
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge alert.
        
        Args:
            alert_id: Alert identifier
            acknowledged_by: User acknowledging
            
        Returns:
            True if successful
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    def resolve_alert(self, alert_id: str, resolution_note: str = None) -> bool:
        """Resolve alert.
        
        Args:
            alert_id: Alert identifier
            resolution_note: Resolution details
            
        Returns:
            True if successful
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "resolved"
        alert.resolved_at = datetime.now()
        
        # Move to history
        self.alert_history.append(alert)
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id}")
        return True
    
    def get_active_alerts(self, severity: str = None) -> list[Alert]:
        """Get active alerts.
        
        Args:
            severity: Filter by severity
            
        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.started_at, reverse=True)
    
    def get_alert_summary(self) -> dict[str, Any]:
        """Get alert summary.
        
        Returns:
            Alert summary
        """
        active = list(self.active_alerts.values())
        
        return {
            "total_active": len(active),
            "by_severity": {
                "critical": len([a for a in active if a.severity == "critical"]),
                "warning": len([a for a in active if a.severity == "warning"]),
                "info": len([a for a in active if a.severity == "info"]),
            },
            "by_source": dict(
                (source, len([a for a in active if a.source == source]))
                for source in set(a.source for a in active)
            ),
        }
    
    def _create_alert(self, rule: AlertRule, current_value: float) -> Alert:
        """Create alert from rule.
        
        Args:
            rule: Alert rule
            current_value: Current metric value
            
        Returns:
            Alert instance
        """
        import uuid
        
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=rule.severity,
            status="firing",
            title=rule.name,
            description=rule.description,
            source="prometheus",
            labels=rule.labels,
            annotations={
                **rule.annotations,
                "current_value": str(current_value),
                "threshold": self._extract_threshold(rule.expression),
            },
            started_at=datetime.now(),
            runbook_url=rule.runbook_url,
        )
        
        return alert
    
    def _is_duplicate(self, new_alert: Alert) -> bool:
        """Check if alert is duplicate.
        
        Args:
            new_alert: New alert to check
            
        Returns:
            True if duplicate
        """
        cutoff = datetime.now() - self.deduplication_window
        
        for alert in self.active_alerts.values():
            if (
                alert.title == new_alert.title
                and alert.labels == new_alert.labels
                and alert.started_at > cutoff
            ):
                return True
        
        return False
    
    def _extract_threshold(self, expression: str) -> float:
        """Extract threshold from expression.
        
        Args:
            expression: PromQL expression
            
        Returns:
            Threshold value
        """
        # Simplified - actual implementation would parse PromQL
        # Example: rate(pipeline_failures[5m]) > 0.05
        parts = expression.split(">")
        if len(parts) == 2:
            try:
                return float(parts[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        
        return 0.0


class AlertDeduplicator:
    """Deduplicate alerts to reduce noise."""
    
    def __init__(self, window_minutes: int = 5):
        """Initialize deduplicator.
        
        Args:
            window_minutes: Deduplication window
        """
        self.window = timedelta(minutes=window_minutes)
        self.seen_alerts: dict[str, datetime] = {}
    
    def is_duplicate(self, alert_key: str) -> bool:
        """Check if alert is duplicate.
        
        Args:
            alert_key: Alert identifier
            
        Returns:
            True if duplicate
        """
        if alert_key in self.seen_alerts:
            last_seen = self.seen_alerts[alert_key]
            if datetime.now() - last_seen < self.window:
                return True
        
        self.seen_alerts[alert_key] = datetime.now()
        return False
    
    def cleanup_old_entries(self) -> None:
        """Remove old entries from deduplication cache."""
        cutoff = datetime.now() - self.window
        self.seen_alerts = {
            k: v for k, v in self.seen_alerts.items()
            if v > cutoff
        }


class AlertRouter:
    """Route alerts to appropriate channels."""
    
    def __init__(self):
        """Initialize alert router."""
        self.routes: dict[str, list[str]] = {}
        self.escalation_policies: dict[str, dict[str, Any]] = {}
    
    def add_route(self, severity: str, channels: list[str]) -> None:
        """Add routing rule.
        
        Args:
            severity: Alert severity
            channels: Notification channels
        """
        self.routes[severity] = channels
    
    def add_escalation_policy(
        self,
        policy_name: str,
        levels: list[dict[str, Any]],
    ) -> None:
        """Add escalation policy.
        
        Args:
            policy_name: Policy name
            levels: Escalation levels
        """
        self.escalation_policies[policy_name] = {
            "levels": levels,
            "current_level": 0,
        }
    
    def route_alert(self, alert: Alert) -> list[str]:
        """Route alert to channels.
        
        Args:
            alert: Alert to route
            
        Returns:
            List of channels to notify
        """
        # Get routes for severity
        channels = self.routes.get(alert.severity, [])
        
        # Add escalation channels if not acknowledged
        if alert.status == "firing":
            channels.extend(self._get_escalation_channels(alert))
        
        return channels
    
    def _get_escalation_channels(self, alert: Alert) -> list[str]:
        """Get escalation channels.
        
        Args:
            alert: Alert
            
        Returns:
            Escalation channels
        """
        # Simplified - actual implementation would check time since firing
        # and escalate based on policy
        return []
    
    def escalate(self, alert: Alert, policy_name: str) -> dict[str, Any]:
        """Escalate alert.
        
        Args:
            alert: Alert to escalate
            policy_name: Escalation policy
            
        Returns:
            Escalation result
        """
        policy = self.escalation_policies.get(policy_name)
        if not policy:
            return {"success": False, "reason": "Policy not found"}
        
        levels = policy["levels"]
        current_level = policy["current_level"]
        
        if current_level >= len(levels):
            return {"success": False, "reason": "Max escalation level reached"}
        
        level = levels[current_level]
        
        # Increment level
        policy["current_level"] += 1
        
        return {
            "success": True,
            "level": current_level + 1,
            "contacts": level.get("contacts", []),
            "channels": level.get("channels", []),
        }


class AlertEnrichment:
    """Enrich alerts with context."""
    
    def __init__(self):
        """Initialize alert enrichment."""
        self.runbooks: dict[str, str] = {}
        self.context_providers: list[callable] = []
    
    def register_runbook(self, alert_name: str, runbook_url: str) -> None:
        """Register runbook.
        
        Args:
            alert_name: Alert name
            runbook_url: Runbook URL
        """
        self.runbooks[alert_name] = runbook_url
    
    def add_context_provider(self, provider: callable) -> None:
        """Add context provider.
        
        Args:
            provider: Context provider function
        """
        self.context_providers.append(provider)
    
    def enrich_alert(self, alert: Alert) -> Alert:
        """Enrich alert with context.
        
        Args:
            alert: Alert to enrich
            
        Returns:
            Enriched alert
        """
        # Add runbook URL
        if alert.title in self.runbooks:
            alert.runbook_url = self.runbooks[alert.title]
        
        # Add context from providers
        for provider in self.context_providers:
            try:
                context = provider(alert)
                alert.annotations.update(context)
            except Exception as e:
                logger.error(f"Context provider failed: {e}")
        
        return alert


class AlertAggregator:
    """Aggregate related alerts."""
    
    def __init__(self):
        """Initialize alert aggregregator."""
        self.alert_groups: dict[str, list[str]] = {}
    
    def group_alerts(self, alerts: list[Alert]) -> dict[str, list[Alert]]:
        """Group related alerts.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Grouped alerts
        """
        groups = defaultdict(list)
        
        for alert in alerts:
            # Group by source and severity
            group_key = f"{alert.source}:{alert.severity}"
            groups[group_key].append(alert)
        
        return dict(groups)
    
    def get_group_summary(self, group_key: str) -> dict[str, Any]:
        """Get group summary.
        
        Args:
            group_key: Group key
            
        Returns:
            Group summary
        """
        alerts = self.alert_groups.get(group_key, [])
        
        return {
            "group_key": group_key,
            "alert_count": len(alerts),
            "severity": alerts[0].severity if alerts else "unknown",
            "first_seen": min(a.started_at for a in alerts) if alerts else None,
            "last_seen": max(a.started_at for a in alerts) if alerts else None,
        }