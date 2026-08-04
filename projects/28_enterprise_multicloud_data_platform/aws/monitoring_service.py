"""
AWS Monitoring Service for Multi-Cloud Data Platform

This module provides AWS CloudWatch monitoring integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MonitoringType(str, Enum):
    """AWS monitoring types"""
    CLOUDWATCH = "cloudwatch"
    CLOUDWATCH_LOGS = "cloudwatch_logs"
    XRAY = "xray"
    EVENT_BRIDGE = "event_bridge"
    SNS = "sns"


class MonitorResource(BaseModel):
    """AWS monitor resource"""
    resource_id: str
    name: str
    region: str
    account_id: str
    monitoring_type: MonitoringType
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AWSMonitoringService:
    """
    AWS monitoring service
    
    This service provides:
    - CloudWatch metrics and alarms
    - CloudWatch Logs
    - X-Ray tracing
    - EventBridge rules
    """
    
    def __init__(self, config: Dict):
        """
        Initialize AWS monitoring service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resources: Dict[str, MonitorResource] = {}
        self.alarms: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AWS Monitoring Service initialized")
    
    async def create_monitor(
        self,
        resource_id: str,
        name: str,
        region: str,
        account_id: str,
        monitoring_type: MonitoringType,
        settings: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> MonitorResource:
        """
        Create monitoring resource
        
        Args:
            resource_id: Resource ID
            name: Resource name
            region: AWS region
            account_id: AWS account ID
            monitoring_type: Monitoring type
            settings: Monitor settings
            tags: Resource tags
            
        Returns:
            Monitor resource
        """
        logger.info(f"Creating AWS monitor: {resource_id}")
        
        if resource_id in self.resources:
            raise ValueError(f"Monitor resource already exists: {resource_id}")
        
        resource = MonitorResource(
            resource_id=resource_id,
            name=name,
            region=region,
            account_id=account_id,
            monitoring_type=monitoring_type,
            settings=settings or {},
            tags=tags or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.resources[resource_id] = resource
        
        logger.info(f"AWS monitor created: {resource_id}")
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
    
    async def create_cloudwatch_alarm(
        self,
        alarm_id: str,
        name: str,
        description: str,
        metric_name: str,
        namespace: str,
        threshold: float,
        comparison_operator: str,
        evaluation_periods: int = 3,
        period: int = 300,
        actions_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create CloudWatch alarm
        
        Args:
            alarm_id: Alarm ID
            name: Alarm name
            description: Alarm description
            metric_name: Metric name
            namespace: Metric namespace
            threshold: Alarm threshold
            comparison_operator: Comparison operator
            evaluation_periods: Number of periods
            period: Metric period in seconds
            actions_enabled: Enable actions
            
        Returns:
            CloudWatch alarm
        """
        logger.info(f"Creating CloudWatch alarm: {alarm_id}")
        
        alarm = {
            "alarm_id": alarm_id,
            "name": name,
            "description": description,
            "metric_name": metric_name,
            "namespace": namespace,
            "threshold": threshold,
            "comparison_operator": comparison_operator,
            "evaluation_periods": evaluation_periods,
            "period": period,
            "actions_enabled": actions_enabled,
            "state": "insufficient_data",
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.alarms[alarm_id] = alarm
        
        return alarm
    
    async def evaluate_metrics(
        self,
        alarm_id: str,
        metric_value: float
    ) -> Dict[str, Any]:
        """
        Evaluate metric against alarm
        
        Args:
            alarm_id: Alarm ID
            metric_value: Current metric value
            
        Returns:
            Alarm evaluation result
        """
        alarm = self.alarms.get(alarm_id)
        if not alarm:
            return {"state": "missing", "reason": "Alarm not found"}
        
        threshold = alarm["threshold"]
        operator = alarm["comparison_operator"]
        
        if operator == "GreaterThanThreshold":
            triggered = metric_value > threshold
        elif operator == "GreaterThanOrEqualToThreshold":
            triggered = metric_value >= threshold
        elif operator == "LessThanThreshold":
            triggered = metric_value < threshold
        elif operator == "LessThanOrEqualToThreshold":
            triggered = metric_value <= threshold
        else:
            triggered = False
        
        alarm["state"] = "alarm" if triggered else "ok"
        
        return {
            "alarm_id": alarm_id,
            "name": alarm["name"],
            "metric": alarm["metric_name"],
            "value": metric_value,
            "threshold": threshold,
            "state": alarm["state"],
            "triggered": triggered
        }
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get monitoring analytics
        
        Returns:
            Monitoring statistics
        """
        total_monitors = len(self.resources)
        total_alarms = len(self.alarms)
        
        # By monitoring type
        by_type = {}
        for resource in self.resources.values():
            monitoring_type = resource.monitoring_type.value
            by_type[monitoring_type] = by_type.get(monitoring_type, 0) + 1
        
        # By region
        by_region = {}
        for resource in self.resources.values():
            region = resource.region
            by_region[region] = by_region.get(region, 0) + 1
        
        # Alarm states
        by_alarm_state = {}
        for alarm in self.alarms.values():
            state = alarm["state"]
            by_alarm_state[state] = by_alarm_state.get(state, 0) + 1
        
        return {
            "total_monitors": total_monitors,
            "total_alarms": total_alarms,
            "by_type": by_type,
            "by_region": by_region,
            "by_alarm_state": by_alarm_state
        }