"""Tests for monitoring components."""

import pytest
from datetime import datetime, timedelta

from monitoring.metrics.collector import (
    MetricsCollector,
    GoldenSignalsCollector,
    SLITracker,
    ErrorBudgetManager,
    MetricType,
)


class TestMetricsCollector:
    """Test metrics collector."""
    
    def test_record_metric(self):
        """Test recording a metric."""
        collector = MetricsCollector()
        
        collector.record_metric(
            name="test_metric",
            value=100.0,
            labels={"service": "test"},
            metric_type=MetricType.GAUGE,
        )
        
        assert len(collector.metrics) == 1
        assert collector.metrics[0].name == "test_metric"
        assert collector.metrics[0].value == 100.0
    
    def test_record_pipeline_metrics(self):
        """Test recording pipeline metrics."""
        collector = MetricsCollector()
        
        collector.record_pipeline_metrics(
            pipeline_id="pipeline-001",
            success=True,
            latency_ms=1500,
            records_processed=1000,
            error_count=0,
        )
        
        # Should record 5 metrics
        assert len(collector.metrics) == 5
        
        # Check specific metrics
        metric_names = [m.name for m in collector.metrics]
        assert "pipeline_execution_count" in metric_names
        assert "pipeline_success" in metric_names
        assert "pipeline_latency" in metric_names
    
    def test_record_streaming_metrics(self):
        """Test recording streaming metrics."""
        collector = MetricsCollector()
        
        collector.record_streaming_metrics(
            topic="events",
            consumer_group="processor",
            messages_per_second=5000,
            consumer_lag=100,
            partition_count=12,
        )
        
        assert len(collector.metrics) == 3
        assert "streaming_messages_per_second" in [m.name for m in collector.metrics]
    
    def test_get_metric(self):
        """Test getting metrics by name."""
        collector = MetricsCollector()
        
        collector.record_metric("metric1", 10.0)
        collector.record_metric("metric1", 20.0)
        collector.record_metric("metric2", 30.0)
        
        metrics = collector.get_metric("metric1")
        assert len(metrics) == 2
        assert all(m.name == "metric1" for m in metrics)
    
    def test_get_stats(self):
        """Test getting metric statistics."""
        collector = MetricsCollector()
        
        # Record some metrics
        for i in range(10):
            collector.record_metric("test", float(i))
        
        stats = collector.get_stats("test", window_minutes=5)
        
        assert "count" in stats
        assert stats["count"] == 10
        assert stats["mean"] == 4.5
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0


class TestGoldenSignalsCollector:
    """Test golden signals collector."""
    
    def test_record_latency(self):
        """Test recording latency."""
        collector = MetricsCollector()
        golden = GoldenSignalsCollector(collector)
        
        golden.record_latency("service-1", 150.0)
        golden.record_latency("service-1", 200.0, endpoint="/api/test")
        
        assert len(collector.metrics) == 2
        assert all(m.name == "golden_signal_latency" for m in collector.metrics)
    
    def test_record_traffic(self):
        """Test recording traffic."""
        collector = MetricsCollector()
        golden = GoldenSignalsCollector(collector)
        
        golden.record_traffic("service-1", 1000.0)
        
        assert len(collector.metrics) == 1
        assert collector.metrics[0].value == 1000.0
    
    def test_record_errors(self):
        """Test recording errors."""
        collector = MetricsCollector()
        golden = GoldenSignalsCollector(collector)
        
        golden.record_errors("service-1", 5, 1000)
        
        assert len(collector.metrics) == 1
        # Error rate should be 0.5%
        assert collector.metrics[0].value == 0.5
    
    def test_record_saturation(self):
        """Test recording saturation."""
        collector = MetricsCollector()
        golden = GoldenSignalsCollector(collector)
        
        golden.record_saturation("service-1", "cpu", 75.0)
        
        assert len(collector.metrics) == 1
        assert collector.metrics[0].value == 75.0


class TestSLITracker:
    """Test SLI tracker."""
    
    def test_define_sli(self):
        """Test defining SLI."""
        tracker = SLITracker(MetricsCollector())
        
        tracker.define_sli(
            name="availability",
            query="avg(up) * 100",
            unit="percent"
        )
        
        assert "availability" in tracker.slis
        assert tracker.slis["availability"]["unit"] == "percent"
    
    def test_update_sli(self):
        """Test updating SLI."""
        tracker = SLITracker(MetricsCollector())
        
        tracker.define_sli("availability", "up", "percent")
        tracker.update_sli("availability", 99.9)
        
        assert tracker.slis["availability"]["current_value"] == 99.9
        assert len(tracker.slis["availability"]["history"]) == 1
    
    def test_update_undefined_sli_raises(self):
        """Test updating undefined SLI raises error."""
        tracker = SLITracker(MetricsCollector())
        
        with pytest.raises(ValueError):
            tracker.update_sli("undefined", 99.9)


class TestErrorBudgetManager:
    """Test error budget manager."""
    
    def test_create_budget(self):
        """Test creating error budget."""
        manager = ErrorBudgetManager()
        
        budget = manager.create_budget(
            name="pipeline-slo",
            slo_target=99.9,
            window_days=30,
        )
        
        assert budget["total_budget"] == 0.1
        assert budget["remaining_budget"] == 0.1
    
    def test_consume_budget(self):
        """Test consuming error budget."""
        manager = ErrorBudgetManager()
        
        manager.create_budget("test", 99.9, 30)
        budget = manager.consume_budget("test", 0.05)
        
        assert budget["consumed_budget"] == 0.05
        assert budget["remaining_budget"] == 0.05
    
    def test_get_budget_status(self):
        """Test getting budget status."""
        manager = ErrorBudgetManager()
        
        manager.create_budget("test", 99.9, 30)
        manager.consume_budget("test", 0.05)
        
        status = manager.get_budget_status("test")
        
        assert status["status"] == "critical"  # 50% consumed
        assert status["remaining_percent"] == 50.0