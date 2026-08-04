"""AI Platform Monitoring & Metrics Collection."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MetricType:
    """Metric type constants."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric(BaseModel):
    """Metric data point."""
    name: str
    value: float
    labels: dict[str, str]
    timestamp: datetime
    metric_type: str


class MetricsCollector:
    """Collect and store AI platform metrics."""
    
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


class AIMetricsCollector:
    """Collect AI-specific metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize AI metrics collector.
        
        Args:
            metrics_collector: Base metrics collector
        """
        self.collector = metrics_collector
    
    def record_llm_request(
        self,
        model: str,
        tokens_prompt: int,
        tokens_completion: int,
        latency_ms: float,
        success: bool,
        user_id: str = None,
    ) -> None:
        """Record LLM request metrics.
        
        Args:
            model: Model name
            tokens_prompt: Prompt token count
            tokens_completion: Completion token count
            latency_ms: Request latency
            success: Whether request succeeded
            user_id: User ID
        """
        labels = {
            "model": model,
            "success": str(success),
        }
        if user_id:
            labels["user_id"] = user_id
        
        self.collector.record_metric("llm_request_count", 1, labels, MetricType.COUNTER)
        self.collector.record_metric("llm_request_latency", latency_ms, labels, MetricType.HISTOGRAM)
        self.collector.record_metric("llm_tokens_prompt", tokens_prompt, labels, MetricType.COUNTER)
        self.collector.record_metric("llm_tokens_completion", tokens_completion, labels, MetricType.COUNTER)
        self.collector.record_metric("llm_total_tokens", tokens_prompt + tokens_completion, labels, MetricType.COUNTER)
    
    def record_rag_retrieval(
        self,
        query: str,
        chunks_retrieved: int,
        retrieval_latency_ms: float,
        rerank_latency_ms: float = 0,
        top_score: float = 0,
    ) -> None:
        """Record RAG retrieval metrics.
        
        Args:
            query: Search query
            chunks_retrieved: Number of chunks retrieved
            retrieval_latency_ms: Retrieval latency
            rerank_latency_ms: Reranking latency
            top_score: Top relevance score
        """
        labels = {"query_length": str(len(query))}
        
        self.collector.record_metric("rag_chunks_retrieved", chunks_retrieved, labels, MetricType.GAUGE)
        self.collector.record_metric("rag_retrieval_latency", retrieval_latency_ms, labels, MetricType.HISTOGRAM)
        
        if rerank_latency_ms > 0:
            self.collector.record_metric("rag_rerank_latency", rerank_latency_ms, labels, MetricType.HISTOGRAM)
        
        if top_score > 0:
            self.collector.record_metric("rag_top_score", top_score, labels, MetricType.GAUGE)
    
    def record_embedding_generation(
        self,
        model: str,
        texts_count: int,
        latency_ms: float,
        token_count: int,
    ) -> None:
        """Record embedding generation metrics.
        
        Args:
            model: Embedding model name
            texts_count: Number of texts embedded
            latency_ms: Generation latency
            token_count: Total token count
        """
        labels = {"model": model}
        
        self.collector.record_metric("embedding_texts_count", texts_count, labels, MetricType.COUNTER)
        self.collector.record_metric("embedding_latency", latency_ms, labels, MetricType.HISTOGRAM)
        self.collector.record_metric("embedding_tokens", token_count, labels, MetricType.COUNTER)
    
    def record_agent_execution(
        self,
        agent_type: str,
        task_id: str,
        execution_time_ms: float,
        success: bool,
        tools_used: list[str] = None,
    ) -> None:
        """Record agent execution metrics.
        
        Args:
            agent_type: Agent type
            task_id: Task ID
            execution_time_ms: Execution time
            success: Whether execution succeeded
            tools_used: List of tools used
        """
        labels = {
            "agent_type": agent_type,
            "success": str(success),
        }
        
        self.collector.record_metric("agent_execution_count", 1, labels, MetricType.COUNTER)
        self.collector.record_metric("agent_execution_time", execution_time_ms, labels, MetricType.HISTOGRAM)
        
        if tools_used:
            for tool in tools_used:
                tool_labels = {**labels, "tool": tool}
                self.collector.record_metric("agent_tool_usage", 1, tool_labels, MetricType.COUNTER)
    
    def record_prompt_evaluation(
        self,
        prompt_id: str,
        version: str,
        relevance_score: float,
        hallucination_score: float,
    ) -> None:
        """Record prompt evaluation metrics.
        
        Args:
            prompt_id: Prompt ID
            version: Prompt version
            relevance_score: Relevance score
            hallucination_score: Hallucination score
        """
        labels = {
            "prompt_id": prompt_id,
            "version": version,
        }
        
        self.collector.record_metric("prompt_relevance", relevance_score, labels, MetricType.GAUGE)
        self.collector.record_metric("prompt_hallucination", hallucination_score, labels, MetricType.GAUGE)


class HealthCheck:
    """Health check for AI platform components."""
    
    def __init__(self):
        """Initialize health check."""
        self.checks: dict[str, callable] = {}
        self.results: dict[str, dict[str, Any]] = {}
    
    def register_check(self, component: str, check_func: callable) -> None:
        """Register health check.
        
        Args:
            component: Component name
            check_func: Health check function
        """
        self.checks[component] = check_func
    
    async def run_checks(self) -> dict[str, dict[str, Any]]:
        """Run all health checks.
        
        Returns:
            Health check results
        """
        import asyncio
        
        results = {}
        
        for component, check_func in self.checks.items():
            try:
                start_time = datetime.now()
                
                if asyncio.iscoroutinefunction(check_func):
                    healthy = await check_func()
                else:
                    healthy = check_func()
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results[component] = {
                    "healthy": healthy,
                    "execution_time_ms": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                results[component] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
        
        self.results = results
        return results
    
    def get_status(self) -> str:
        """Get overall health status.
        
        Returns:
            Status string
        """
        if not self.results:
            return "unknown"
        
        all_healthy = all(r.get("healthy", False) for r in self.results.values())
        
        if all_healthy:
            return "healthy"
        else:
            return "unhealthy"


class AlertManager:
    """Manage alerts for AI platform."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.alerts: list[dict[str, Any]] = []
        self.rules: list[dict[str, Any]] = []
    
    def add_rule(self, rule: dict[str, Any]) -> None:
        """Add alert rule.
        
        Args:
            rule: Alert rule definition
        """
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.get('name')}")
    
    def evaluate_rules(self, metrics_collector: MetricsCollector) -> list[dict[str, Any]]:
        """Evaluate alert rules.
        
        Args:
            metrics_collector: Metrics collector
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        for rule in self.rules:
            metric_name = rule.get("metric")
            threshold = rule.get("threshold")
            condition = rule.get("condition", "greater_than")
            window_minutes = rule.get("window_minutes", 5)
            
            stats = metrics_collector.get_stats(metric_name, window_minutes)
            
            if not stats:
                continue
            
            value = stats.get("mean", 0)
            triggered = False
            
            if condition == "greater_than" and value > threshold:
                triggered = True
            elif condition == "less_than" and value < threshold:
                triggered = True
            elif condition == "equals" and value == threshold:
                triggered = True
            
            if triggered:
                alert = {
                    "rule": rule.get("name"),
                    "severity": rule.get("severity", "warning"),
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "timestamp": datetime.now(),
                }
                triggered_alerts.append(alert)
                self.alerts.append(alert)
        
        return triggered_alerts
    
    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get active alerts.
        
        Returns:
            List of active alerts
        """
        # Return alerts from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        return [a for a in self.alerts if a["timestamp"] > cutoff]


class CostTracker:
    """Track AI platform costs."""
    
    def __init__(self):
        """Initialize cost tracker."""
        self.costs: list[dict[str, Any]] = []
    
    def record_cost(
        self,
        service: str,
        cost: float,
        currency: str = "USD",
        metadata: dict[str, Any] = None,
    ) -> None:
        """Record cost.
        
        Args:
            service: Service name
            cost: Cost amount
            currency: Currency code
            metadata: Additional metadata
        """
        cost_record = {
            "service": service,
            "cost": cost,
            "currency": currency,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
        }
        
        self.costs.append(cost_record)
    
    def get_total_cost(self, start_time: datetime = None, end_time: datetime = None) -> float:
        """Get total cost.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            Total cost
        """
        filtered = self.costs
        
        if start_time:
            filtered = [c for c in filtered if c["timestamp"] >= start_time]
        
        if end_time:
            filtered = [c for c in filtered if c["timestamp"] <= end_time]
        
        return sum(c["cost"] for c in filtered)
    
    def get_cost_by_service(self, start_time: datetime = None, end_time: datetime = None) -> dict[str, float]:
        """Get cost breakdown by service.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            Cost by service
        """
        filtered = self.costs
        
        if start_time:
            filtered = [c for c in filtered if c["timestamp"] >= start_time]
        
        if end_time:
            filtered = [c for c in filtered if c["timestamp"] <= end_time]
        
        costs_by_service = defaultdict(float)
        for c in filtered:
            costs_by_service[c["service"]] += c["cost"]
        
        return dict(costs_by_service)