"""
Metrics Collector for Cross-Cloud Observability

This module provides unified metrics collection across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric(BaseModel):
    """Metric definition"""
    metric_id: str
    name: str
    description: str
    metric_type: MetricType
    unit: str
    labels: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MetricDataPoint(BaseModel):
    """Metric data point"""
    metric_id: str
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricsCollector:
    """
    Cross-cloud metrics collector
    
    This service provides:
    - Metrics collection and aggregation
    - Cross-cloud metric normalization
    - Metric storage and querying
    - Metric analytics
    """
    
    def __init__(self, config: Dict):
        """
        Initialize metrics collector
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.metrics: Dict[str, Metric] = {}
        self.data_points: List[MetricDataPoint] = []
        self.retention_days = config.get("retention_days", 90)
        
        logger.info("Metrics Collector initialized")
    
    async def register_metric(
        self,
        metric_id: str,
        name: str,
        description: str,
        metric_type: MetricType,
        unit: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Metric:
        """
        Register new metric
        
        Args:
            metric_id: Metric ID
            name: Metric name
            description: Metric description
            metric_type: Metric type
            unit: Metric unit
            labels: Metric labels
            
        Returns:
            Metric
        """
        logger.info(f"Registering metric: {metric_id}")
        
        if metric_id in self.metrics:
            raise ValueError(f"Metric already exists: {metric_id}")
        
        metric = Metric(
            metric_id=metric_id,
            name=name,
            description=description,
            metric_type=metric_type,
            unit=unit,
            labels=labels or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.metrics[metric_id] = metric
        
        logger.info(f"Metric registered: {metric_id}")
        return metric
    
    async def record_metric(
        self,
        metric_id: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> MetricDataPoint:
        """
        Record metric data point
        
        Args:
            metric_id: Metric ID
            value: Metric value
            labels: Metric labels
            timestamp: Timestamp (defaults to now)
            
        Returns:
            Metric data point
        """
        if metric_id not in self.metrics:
            raise ValueError(f"Metric not found: {metric_id}")
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        data_point = MetricDataPoint(
            metric_id=metric_id,
            timestamp=timestamp,
            value=value,
            labels=labels or {}
        )
        
        self.data_points.append(data_point)
        
        # Cleanup old data points
        await self._cleanup_old_data()
        
        return data_point
    
    async def _cleanup_old_data(self) -> None:
        """Cleanup old data points"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        self.data_points = [
            dp for dp in self.data_points
            if dp.timestamp >= cutoff_date
        ]
    
    async def query_metrics(
        self,
        metric_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
        aggregation: Optional[str] = None,
        interval: Optional[str] = None
    ) -> List[MetricDataPoint]:
        """
        Query metric data
        
        Args:
            metric_id: Metric ID
            start_time: Start time (optional)
            end_time: End time (optional)
            labels: Labels filter (optional)
            aggregation: Aggregation function (sum, avg, min, max)
            interval: Aggregation interval (e.g., "1h", "5m")
            
        Returns:
            List of metric data points
        """
        if metric_id not in self.metrics:
            return []
        
        # Filter data points
        results = [dp for dp in self.data_points if dp.metric_id == metric_id]
        
        if start_time:
            results = [dp for dp in results if dp.timestamp >= start_time]
        
        if end_time:
            results = [dp for dp in results if dp.timestamp <= end_time]
        
        if labels:
            for key, value in labels.items():
                results = [dp for dp in results if dp.labels.get(key) == value]
        
        # Sort by timestamp
        results.sort(key=lambda dp: dp.timestamp)
        
        # Apply aggregation
        if aggregation and interval:
            results = await self._aggregate_metrics(results, aggregation, interval)
        
        return results
    
    async def _aggregate_metrics(
        self,
        data_points: List[MetricDataPoint],
        aggregation: str,
        interval: str
    ) -> List[MetricDataPoint]:
        """
        Aggregate metrics
        
        Args:
            data_points: Data points
            aggregation: Aggregation function
            interval: Aggregation interval
            
        Returns:
            Aggregated data points
        """
        # Simplified aggregation
        # In real implementation, use proper time-based bucketing
        
        if not data_points:
            return []
        
        # Group by hour for simplicity
        buckets: Dict[str, List[float]] = {}
        
        for dp in data_points:
            bucket_key = dp.timestamp.strftime("%Y-%m-%d %H:00")
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append(dp.value)
        
        # Aggregate
        aggregated = []
        for bucket_key, values in buckets.items():
            if aggregation == "sum":
                value = sum(values)
            elif aggregation == "avg":
                value = sum(values) / len(values)
            elif aggregation == "min":
                value = min(values)
            elif aggregation == "max":
                value = max(values)
            else:
                value = sum(values)
            
            aggregated.append(MetricDataPoint(
                metric_id=data_points[0].metric_id,
                timestamp=datetime.strptime(bucket_key, "%Y-%m-%d %H:00"),
                value=value,
                labels=data_points[0].labels
            ))
        
        return aggregated
    
    async def get_metric(self, metric_id: str) -> Optional[Metric]:
        """
        Get metric by ID
        
        Args:
            metric_id: Metric ID
            
        Returns:
            Metric if found, None otherwise
        """
        return self.metrics.get(metric_id)
    
    async def list_metrics(
        self,
        metric_type: Optional[MetricType] = None
    ) -> List[Metric]:
        """
        List metrics
        
        Args:
            metric_type: Metric type filter
            
        Returns:
            List of metrics
        """
        metrics = list(self.metrics.values())
        
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        return metrics
    
    async def get_metrics_analytics(self) -> Dict[str, Any]:
        """
        Get metrics analytics
        
        Returns:
            Metrics statistics
        """
        total_metrics = len(self.metrics)
        total_data_points = len(self.data_points)
        
        # By metric type
        by_type = {}
        for metric in self.metrics.values():
            metric_type = metric.metric_type.value
            by_type[metric_type] = by_type.get(metric_type, 0) + 1
        
        # Recent data points (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_points = len([dp for dp in self.data_points if dp.timestamp >= cutoff])
        
        return {
            "total_metrics": total_metrics,
            "total_data_points": total_data_points,
            "recent_data_points_1h": recent_points,
            "by_type": by_type
        }