"""Metrics Collector - Comprehensive metrics collection for data platform monitoring."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Metric(BaseModel):
    """Metric data point."""
    name: str
    value: float
    labels: dict[str, str]
    timestamp: datetime
    metric_type: str  # counter, gauge, histogram, summary


class MetricType:
    """Metric type constants."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricsCollector:
    """Collect and store platform metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: list[Metric] = []
        self.aggregated: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    
    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] = None,
        metric_type: str = MetricType.GAUGE,
    ) -> None:
        """Record a metric.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Metric labels
            metric_type: Type of metric
        """
        metric = Metric(
            name=name,
            value=value,
            labels=labels or {},
            timestamp=datetime.now(),
            metric_type=metric_type,
        )
        
        self.metrics.append(metric)
        
        # Aggregate by name and labels
        label_key = ",".join(f"{k}={v}" for k, v in sorted(metric.labels.items()))
        self.aggregated[name][label_key].append(value)
    
    def record_pipeline_metrics(
        self,
        pipeline_id: str,
        success: bool,
        latency_ms: float,
        records_processed: int,
        error_count: int = 0,
    ) -> None:
        """Record pipeline execution metrics.
        
        Args:
            pipeline_id: Pipeline identifier
            success: Whether pipeline succeeded
            latency_ms: Execution latency
            records_processed: Number of records processed
            error_count: Number of errors
        """
        labels = {"pipeline_id": pipeline_id}
        
        self.record_metric("pipeline_execution_count", 1, labels, MetricType.COUNTER)
        self.record_metric("pipeline_success", 1 if success else 0, labels, MetricType.GAUGE)
        self.record_metric("pipeline_latency", latency_ms, labels, MetricType.HISTOGRAM)
        self.record_metric("pipeline_records_processed", records_processed, labels, MetricType.COUNTER)
        self.record_metric("pipeline_errors", error_count, labels, MetricType.COUNTER)
    
    def record_streaming_metrics(
        self,
        topic: str,
        consumer_group: str,
        messages_per_second: float,
        consumer_lag: int,
        partition_count: int,
    ) -> None:
        """Record streaming metrics.
        
        Args:
            topic: Kafka topic
            consumer_group: Consumer group
            messages_per_second: Messages per second
            consumer_lag: Consumer lag
            partition_count: Number of partitions
        """
        labels = {
            "topic": topic,
            "consumer_group": consumer_group,
        }
        
        self.record_metric("streaming_messages_per_second", messages_per_second, labels, MetricType.GAUGE)
        self.record_metric("streaming_consumer_lag", consumer_lag, labels, MetricType.GAUGE)
        self.record_metric("streaming_partition_count", partition_count, labels, MetricType.GAUGE)
    
    def record_infrastructure_metrics(
        self,
        component: str,
        cpu_percent: float,
        memory_percent: float,
        disk_io: float,
        network_io: float,
    ) -> None:
        """Record infrastructure metrics.
        
        Args:
            component: Component name
            cpu_percent: CPU utilization
            memory_percent: Memory utilization
            disk_io: Disk I/O
            network_io: Network I/O
        """
        labels = {"component": component}
        
        self.record_metric("infrastructure_cpu", cpu_percent, labels, MetricType.GAUGE)
        self.record_metric("infrastructure_memory", memory_percent, labels, MetricType.GAUGE)
        self.record_metric("infrastructure_disk_io", disk_io, labels, MetricType.GAUGE)
        self.record_metric("infrastructure_network_io", network_io, labels, MetricType.GAUGE)
    
    def record_ai_metrics(
        self,
        model_id: str,
        inference_latency_ms: float,
        tokens_used: int,
        cost: float,
        success: bool,
    ) -> None:
        """Record AI platform metrics.
        
        Args:
            model_id: Model identifier
            inference_latency_ms: Inference latency
            tokens_used: Tokens consumed
            cost: Inference cost
            success: Whether inference succeeded
        """
        labels = {"model_id": model_id}
        
        self.record_metric("ai_inference_latency", inference_latency_ms, labels, MetricType.HISTOGRAM)
        self.record_metric("ai_tokens_used", tokens_used, labels, MetricType.COUNTER)
        self.record_metric("ai_cost", cost, labels, MetricType.COUNTER)
        self.record_metric("ai_inference_success", 1 if success else 0, labels, MetricType.GAUGE)
    
    def get_metric(
        self,
        name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        labels: dict[str, str] = None,
    ) -> list[Metric]:
        """Get metrics by name.
        
        Args:
            name: Metric name
            start_time: Start time filter
            end_time: End time filter
            labels: Label filter
            
        Returns:
            List of metrics
        """
        filtered = [m for m in self.metrics if m.name == name]
        
        if start_time:
            filtered = [m for m in filtered if m.timestamp >= start_time]
        
        if end_time:
            filtered = [m for m in filtered if m.timestamp <= end_time]
        
        if labels:
            filtered = [
                m for m in filtered
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]
        
        return filtered
    
    def get_stats(self, name: str, window_minutes: int = 5) -> dict[str, float]:
        """Get metric statistics.
        
        Args:
            name: Metric name
            window_minutes: Time window in minutes
            
        Returns:
            Statistics dictionary
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        metrics = self.get_metric(name, start_time, end_time)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }
    
    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile.
        
        Args:
            values: List of values
            percentile: Percentile (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        
        return sorted_values[min(index, len(sorted_values) - 1)]


class GoldenSignalsCollector:
    """Collect golden signals for services."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize golden signals collector.
        
        Args:
            metrics_collector: Base metrics collector
        """
        self.collector = metrics_collector
    
    def record_latency(self, service: str, latency_ms: float, endpoint: str = None) -> None:
        """Record latency metric.
        
        Args:
            service: Service name
            latency_ms: Latency in milliseconds
            endpoint: API endpoint
        """
        labels = {"service": service}
        if endpoint:
            labels["endpoint"] = endpoint
        
        self.collector.record_metric(
            "golden_signal_latency",
            latency_ms,
            labels,
            MetricType.HISTOGRAM
        )
    
    def record_traffic(self, service: str, requests_per_second: float) -> None:
        """Record traffic metric.
        
        Args:
            service: Service name
            requests_per_second: Requests per second
        """
        labels = {"service": service}
        
        self.collector.record_metric(
            "golden_signal_traffic",
            requests_per_second,
            labels,
            MetricType.GAUGE
        )
    
    def record_errors(self, service: str, error_count: int, total_requests: int) -> None:
        """Record error metric.
        
        Args:
            service: Service name
            error_count: Number of errors
            total_requests: Total requests
        """
        labels = {"service": service}
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        self.collector.record_metric(
            "golden_signal_errors",
            error_rate,
            labels,
            MetricType.GAUGE
        )
    
    def record_saturation(self, service: str, resource: str, utilization_percent: float) -> None:
        """Record saturation metric.
        
        Args:
            service: Service name
            resource: Resource type (cpu, memory, disk)
            utilization_percent: Utilization percentage
        """
        labels = {
            "service": service,
            "resource": resource,
        }
        
        self.collector.record_metric(
            "golden_signal_saturation",
            utilization_percent,
            labels,
            MetricType.GAUGE
        )


class SLITracker:
    """Track Service Level Indicators."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize SLI tracker.
        
        Args:
            metrics_collector: Base metrics collector
        """
        self.collector = metrics_collector
        self.slis: dict[str, dict[str, Any]] = {}
    
    def define_sli(self, name: str, query: str, unit: str = "percent") -> None:
        """Define SLI.
        
        Args:
            name: SLI name
            query: PromQL query
            unit: Unit of measurement
        """
        self.slis[name] = {
            "query": query,
            "unit": unit,
            "current_value": 0.0,
            "history": [],
        }
    
    def update_sli(self, name: str, value: float) -> None:
        """Update SLI value.
        
        Args:
            name: SLI name
            value: SLI value
        """
        if name not in self.slis:
            raise ValueError(f"SLI not defined: {name}")
        
        self.slis[name]["current_value"] = value
        self.slis[name]["history"].append({
            "timestamp": datetime.now(),
            "value": value,
        })
    
    def get_sli(self, name: str) -> dict[str, Any]:
        """Get SLI data.
        
        Args:
            name: SLI name
            
        Returns:
            SLI data
        """
        if name not in self.slis:
            return {}
        
        return self.slis[name]


class ErrorBudgetManager:
    """Manage error budgets for SLOs."""
    
    def __init__(self):
        """Initialize error budget manager."""
        self.budgets: dict[str, dict[str, Any]] = {}
    
    def create_budget(
        self,
        name: str,
        slo_target: float,
        window_days: int,
    ) -> dict[str, Any]:
        """Create error budget.
        
        Args:
            name: Budget name
            slo_target: SLO target (e.g., 99.9)
            window_days: Time window in days
            
        Returns:
            Budget configuration
        """
        budget = {
            "name": name,
            "slo_target": slo_target,
            "window_days": window_days,
            "total_budget": 100 - slo_target,
            "remaining_budget": 100 - slo_target,
            "consumed_budget": 0.0,
            "start_time": datetime.now(),
        }
        
        self.budgets[name] = budget
        return budget
    
    def consume_budget(self, name: str, amount: float) -> dict[str, Any]:
        """Consume error budget.
        
        Args:
            name: Budget name
            amount: Amount to consume
            
        Returns:
            Updated budget
        """
        if name not in self.budgets:
            raise ValueError(f"Budget not found: {name}")
        
        budget = self.budgets[name]
        budget["consumed_budget"] += amount
        budget["remaining_budget"] = budget["total_budget"] - budget["consumed_budget"]
        
        return budget
    
    def get_budget_status(self, name: str) -> dict[str, Any]:
        """Get budget status.
        
        Args:
            name: Budget name
            
        Returns:
            Budget status
        """
        if name not in self.budgets:
            return {}
        
        budget = self.budgets[name]
        
        return {
            "name": name,
            "total_budget": budget["total_budget"],
            "consumed_budget": budget["consumed_budget"],
            "remaining_budget": budget["remaining_budget"],
            "remaining_percent": (budget["remaining_budget"] / budget["total_budget"] * 100) if budget["total_budget"] > 0 else 0,
            "status": self._get_budget_status(budget["remaining_budget"], budget["total_budget"]),
        }
    
    def _get_budget_status(self, remaining: float, total: float) -> str:
        """Get budget status.
        
        Args:
            remaining: Remaining budget
            total: Total budget
            
        Returns:
            Status string
        """
        if total == 0:
            return "healthy"
        
        ratio = remaining / total
        
        if ratio > 0.5:
            return "healthy"
        elif ratio > 0.1:
            return "warning"
        elif ratio > 0:
            return "critical"
        else:
            return "exhausted"