"""
Alert Manager for Cross-Cloud Observability

This module provides unified alerting across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class Alert(BaseModel):
    """Alert definition"""
    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    resource_id: str
    resource_type: str
    cloud: str
    condition: Dict[str, Any]
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AlertRule(BaseModel):
    """Alert rule"""
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: Dict[str, Any]
    resource_type: str
    cloud: str
    enabled: bool = True
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AlertManager:
    """
    Cross-cloud alert manager
    
    This service provides:
    - Alert rule management
    - Alert evaluation and firing
    - Alert routing and notification
    - Alert lifecycle management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize alert manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        
        logger.info("Alert Manager initialized")
    
    async def create_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: AlertSeverity,
        condition: Dict[str, Any],
        resource_type: str,
        cloud: str,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AlertRule:
        """
        Create alert rule
        
        Args:
            rule_id: Rule ID
            name: Rule name
            description: Rule description
            severity: Alert severity
            condition: Alert condition
            resource_type: Resource type
            cloud: Cloud provider
            labels: Rule labels
            metadata: Additional metadata
            
        Returns:
            Alert rule
        """
        logger.info(f"Creating alert rule: {rule_id}")
        
        if rule_id in self.rules:
            raise ValueError(f"Alert rule already exists: {rule_id}")
        
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            description=description,
            severity=severity,
            condition=condition,
            resource_type=resource_type,
            cloud=cloud,
            labels=labels or {},
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.rules[rule_id] = rule
        
        logger.info(f"Alert rule created: {rule_id}")
        return rule
    
    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        Get alert rule by ID
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Alert rule if found, None otherwise
        """
        return self.rules.get(rule_id)
    
    async def evaluate_condition(
        self,
        rule_id: str,
        resource_id: str,
        metrics: Dict[str, float],
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[Alert]:
        """
        Evaluate alert rule condition
        
        Args:
            rule_id: Rule ID
            resource_id: Resource ID
            metrics: Current metrics
            labels: Additional labels
            
        Returns:
            Alert if condition met, None otherwise
        """
        rule = self.rules.get(rule_id)
        if not rule:
            logger.warning(f"Alert rule not found: {rule_id}")
            return None
        
        if not rule.enabled:
            return None
        
        # Check if condition is met
        condition_met = self._check_condition(rule.condition, metrics)
        
        if condition_met:
            # Create alert
            alert_id = f"alert-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{resource_id[:8]}"
            
            alert = Alert(
                alert_id=alert_id,
                name=rule.name,
                description=rule.description,
                severity=rule.severity,
                status=AlertStatus.FIRING,
                resource_id=resource_id,
                resource_type=rule.resource_type,
                cloud=rule.cloud,
                condition=rule.condition,
                labels={**rule.labels, **(labels or {})},
                metadata=rule.metadata,
                started_at=datetime.utcnow()
            )
            
            self.alerts[alert_id] = alert
            
            logger.info(f"Alert fired: {alert_id}")
            return alert
        
        return None
    
    def _check_condition(self, condition: Dict[str, Any], metrics: Dict[str, float]) -> bool:
        """
        Check if alert condition is met
        
        Args:
            condition: Alert condition
            metrics: Current metrics
            
        Returns:
            True if condition met, False otherwise
        """
        metric_name = condition.get("metric")
        threshold = condition.get("threshold")
        operator = condition.get("operator", ">")
        
        if metric_name not in metrics:
            return False
        
        value = metrics[metric_name]
        
        if operator == ">":
            return value > threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<":
            return value < threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        
        return False
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> Optional[Alert]:
        """
        Acknowledge alert
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged
            
        Returns:
            Updated alert
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            logger.warning(f"Alert not found: {alert_id}")
            return None
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert acknowledged: {alert_id}")
        return alert
    
    async def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Resolve alert
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Updated alert
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            logger.warning(f"Alert not found: {alert_id}")
            return None
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        
        logger.info(f"Alert resolved: {alert_id}")
        return alert
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Get alert by ID
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Alert if found, None otherwise
        """
        return self.alerts.get(alert_id)
    
    async def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        cloud: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> List[Alert]:
        """
        List alerts
        
        Args:
            status: Alert status filter
            severity: Alert severity filter
            cloud: Cloud provider filter
            resource_id: Resource ID filter
            
        Returns:
            List of alerts
        """
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if cloud:
            alerts = [a for a in alerts if a.cloud == cloud]
        
        if resource_id:
            alerts = [a for a in alerts if a.resource_id == resource_id]
        
        # Sort by started_at desc
        alerts.sort(key=lambda a: a.started_at, reverse=True)
        
        return alerts
    
    async def get_active_alerts(self) -> List[Alert]:
        """
        Get active alerts
        
        Returns:
            List of active alerts
        """
        return [a for a in self.alerts.values() if a.status == AlertStatus.FIRING]
    
    async def get_alert_analytics(self) -> Dict[str, Any]:
        """
        Get alert analytics
        
        Returns:
            Alert statistics
        """
        total_alerts = len(self.alerts)
        
        # By status
        by_status = {}
        for alert in self.alerts.values():
            status = alert.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By severity
        by_severity = {}
        for alert in self.alerts.values():
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # By cloud
        by_cloud = {}
        for alert in self.alerts.values():
            cloud = alert.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # Active alerts
        active = len([a for a in self.alerts.values() if a.status == AlertStatus.FIRING])
        
        # Recent alerts (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = len([a for a in self.alerts.values() if a.started_at >= cutoff])
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active,
            "recent_alerts_24h": recent,
            "by_status": by_status,
            "by_severity": by_severity,
            "by_cloud": by_cloud
        }