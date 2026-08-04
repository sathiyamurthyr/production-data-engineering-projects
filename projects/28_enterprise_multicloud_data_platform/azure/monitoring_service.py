"""
Azure Monitoring Service for Multi-Cloud Data Platform

This module provides Azure monitoring and observability integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MonitoringType(str, Enum):
    """Azure monitoring types"""
    METRICS = "metrics"
    LOGS = "logs"
    ALERTS = "alerts"
    DIAGNOSTICS = "diagnostics"
    APPLICATION_INSIGHTS = "application_insights"


class MonitorResource(BaseModel):
    """Azure monitor resource"""
    resource_id: str
    name: str
    resource_group: str
    location: str
    monitoring_type: MonitoringType
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AzureMonitoringService:
    """
    Azure monitoring service
    
    This service provides:
    - Azure Monitor integration
    - Log Analytics workspaces
    - Application Insights
    - Alert rules
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Azure monitoring service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resources: Dict[str, MonitorResource] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Azure Monitoring Service initialized")
    
    async def create_monitor(
        self,
        resource_id: str,
        name: str,
        resource_group: str,
        location: str,
        monitoring_type: MonitoringType,
        settings: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> MonitorResource:
        """
        Create monitoring resource
        
        Args:
            resource_id: Resource ID
            name: Resource name
            resource_group: Resource group
            location: Azure region
            monitoring_type: Monitoring type
            settings: Monitor settings
            tags: Resource tags
            
        Returns:
            Monitor resource
        """
        logger.info(f"Creating Azure monitor: {resource_id}")
        
        if resource_id in self.resources:
            raise ValueError(f"Monitor resource already exists: {resource_id}")
        
        resource = MonitorResource(
            resource_id=resource_id,
            name=name,
            resource_group=resource_group,
            location=location,
            monitoring_type=monitoring_type,
            settings=settings or {},
            tags=tags or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.resources[resource_id] = resource
        
        logger.info(f"Azure monitor created: {resource_id}")
        return resource
    
    async def get_monitor(self, resource_id: str) -> Optional[MonitorResource]:
        """
        Get monitor resource by ID
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Monitor resource if found, None otherwise
        """
        return self.resources.get(resource_id)
    
    async def list_monitors(
        self,
        monitoring_type: Optional[MonitoringType] = None,
        resource_group: Optional[str] = None
    ) -> List[MonitorResource]:
        """
        List monitor resources
        
        Args:
            monitoring_type: Monitoring type filter
            resource_group: Resource group filter
            
        Returns:
            List of monitor resources
        """
        resources = list(self.resources.values())
        
        if monitoring_type:
            resources = [r for r in resources if r.monitoring_type == monitoring_type]
        
        if resource_group:
            resources = [r for r in resources if r.resource_group == resource_group]
        
        return resources
    
    async def create_alert_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: int,
        resource_id: str,
        condition: Dict[str, Any],
        action_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create alert rule
        
        Args:
            rule_id: Rule ID
            name: Rule name
            description: Rule description
            severity: Severity (0-4)
            resource_id: Target resource
            condition: Alert condition
            action_group_id: Action group ID
            
        Returns:
            Alert rule
        """
        logger.info(f"Creating alert rule: {rule_id}")
        
        rule = {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "severity": severity,
            "resource_id": resource_id,
            "condition": condition,
            "action_group_id": action_group_id,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.alert_rules[rule_id] = rule
        
        return rule
    
    async def evaluate_alert(
        self,
        rule_id: str,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluate alert rule
        
        Args:
            rule_id: Rule ID
            metrics: Current metrics
            
        Returns:
            Alert evaluation result
        """
        rule = self.alert_rules.get(rule_id)
        if not rule:
            return {"triggered": False, "reason": "Rule not found"}
        
        condition = rule["condition"]
        metric_name = condition.get("metric")
        threshold = condition.get("threshold")
        operator = condition.get("operator", ">")
        
        if metric_name not in metrics:
            return {"triggered": False, "reason": "Metric not available"}
        
        value = metrics[metric_name]
        
        if operator == ">":
            triggered = value > threshold
        elif operator == ">=":
            triggered = value >= threshold
        elif operator == "<":
            triggered = value < threshold
        elif operator == "<=":
            triggered = value <= threshold
        else:
            triggered = False
        
        return {
            "triggered": triggered,
            "rule_id": rule_id,
            "rule_name": rule["name"],
            "metric": metric_name,
            "value": value,
            "threshold": threshold,
            "operator": operator
        }
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get monitoring analytics
        
        Returns:
            Monitoring statistics
        """
        total_monitors = len(self.resources)
        total_alerts = len(self.alert_rules)
        
        # By monitoring type
        by_type = {}
        for resource in self.resources.values():
            monitoring_type = resource.monitoring_type.value
            by_type[monitoring_type] = by_type.get(monitoring_type, 0) + 1
        
        # By location
        by_location = {}
        for resource in self.resources.values():
            location = resource.location
            by_location[location] = by_location.get(location, 0) + 1
        
        return {
            "total_monitors": total_monitors,
            "total_alert_rules": total_alerts,
            "enabled_alerts": len([r for r in self.alert_rules.values() if r["enabled"]]),
            "by_type": by_type,
            "by_location": by_location
        }