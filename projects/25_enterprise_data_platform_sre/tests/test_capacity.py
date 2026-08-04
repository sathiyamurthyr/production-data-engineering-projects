"""Tests for capacity planning components."""

import pytest
from datetime import datetime, timedelta

from capacity.forecaster import (
    CapacityPlanner,
    CapacityOptimizer,
    CostAnalyzer,
    MetricData,
    ForecastResult,
    ScalingRecommendation,
)


class TestCapacityPlanner:
    """Test capacity planner."""
    
    def test_load_historical_data(self):
        """Test loading historical data."""
        planner = CapacityPlanner()
        
        data = [
            MetricData(timestamp=datetime.now() - timedelta(days=i), value=100.0 + i)
            for i in range(30)
        ]
        
        planner.load_historical_data("cpu_usage", data)
        
        assert "cpu_usage" in planner.historical_data
        assert len(planner.historical_data["cpu_usage"]) == 30
    
    def test_forecast_growth(self):
        """Test forecasting growth."""
        planner = CapacityPlanner()
        
        # Load historical data
        data = [
            MetricData(timestamp=datetime.now() - timedelta(days=i), value=100.0 + i * 2)
            for i in range(30)
        ]
        planner.load_historical_data("cpu_usage", data)
        
        # Forecast
        forecast = planner.forecast_growth("cpu_usage", days_ahead=7)
        
        assert isinstance(forecast, ForecastResult)
        assert forecast.metric_name == "cpu_usage"
        assert len(forecast.predicted_values) == 7
        assert len(forecast.forecast_dates) == 7
        assert forecast.model_accuracy > 0
    
    def test_forecast_growth_insufficient_data(self):
        """Test forecasting with insufficient data."""
        planner = CapacityPlanner()
        
        data = [
            MetricData(timestamp=datetime.now(), value=100.0)
        ]
        planner.load_historical_data("test", data)
        
        with pytest.raises(ValueError):
            planner.forecast_growth("test", days_ahead=7)
    
    def test_forecast_growth_undefined_metric(self):
        """Test forecasting undefined metric."""
        planner = CapacityPlanner()
        
        with pytest.raises(ValueError):
            planner.forecast_growth("undefined", days_ahead=7)
    
    def test_recommend_scaling_scale_up(self):
        """Test scaling recommendation - scale up."""
        planner = CapacityPlanner()
        
        data = [
            MetricData(timestamp=datetime.now() - timedelta(days=i), value=100.0 + i * 3)
            for i in range(30)
        ]
        planner.load_historical_data("cpu", data)
        
        recommendation = planner.recommend_scaling(
            metric_name="cpu",
            current_usage=80.0,
            max_capacity=100.0,
        )
        
        assert isinstance(recommendation, ScalingRecommendation)
        assert recommendation.action == "scale_up"
        assert recommendation.urgency in ["immediate", "planned"]
    
    def test_recommend_scaling_maintain(self):
        """Test scaling recommendation - maintain."""
        planner = CapacityPlanner()
        
        data = [
            MetricData(timestamp=datetime.now() - timedelta(days=i), value=50.0)
            for i in range(30)
        ]
        planner.load_historical_data("cpu", data)
        
        recommendation = planner.recommend_scaling(
            metric_name="cpu",
            current_usage=40.0,
            max_capacity=100.0,
        )
        
        assert recommendation.action == "maintain"
        assert recommendation.urgency == "monitor"


class TestCapacityOptimizer:
    """Test capacity optimizer."""
    
    def test_register_resource(self):
        """Test registering resource."""
        optimizer = CapacityOptimizer()
        
        optimizer.register_resource(
            resource_name="cluster-1",
            current_capacity=100.0,
            utilization=20.0,
            cost_per_unit=10.0,
        )
        
        assert "cluster-1" in optimizer.resources
    
    def test_optimize_underutilized(self):
        """Test optimization with underutilized resource."""
        optimizer = CapacityOptimizer()
        
        optimizer.register_resource(
            resource_name="cluster-1",
            current_capacity=100.0,
            utilization=20.0,
            cost_per_unit=10.0,
        )
        
        result = optimizer.optimize()
        
        assert result["optimization_count"] > 0
        assert result["recommendations"][0]["action"] == "scale_down"
        assert result["total_monthly_savings"] > 0
    
    def test_optimize_overutilized(self):
        """Test optimization with overutilized resource."""
        optimizer = CapacityOptimizer()
        
        optimizer.register_resource(
            resource_name="cluster-1",
            current_capacity=100.0,
            utilization=90.0,
            cost_per_unit=10.0,
        )
        
        result = optimizer.optimize()
        
        assert result["optimization_count"] > 0
        assert result["recommendations"][0]["action"] == "scale_up"


class TestCostAnalyzer:
    """Test cost analyzer."""
    
    def test_record_cost(self):
        """Test recording cost."""
        analyzer = CostAnalyzer()
        
        analyzer.record_cost(
            service="databricks",
            cost=1000.0,
            timestamp=datetime.now(),
        )
        
        assert "databricks" in analyzer.cost_data
        assert len(analyzer.cost_data["databricks"]) == 1
    
    def test_get_cost_analysis(self):
        """Test getting cost analysis."""
        analyzer = CostAnalyzer()
        
        # Record costs over multiple days
        for i in range(30):
            analyzer.record_cost(
                service="databricks",
                cost=1000.0 + i * 10,
                timestamp=datetime.now() - timedelta(days=i),
            )
        
        analysis = analyzer.get_cost_analysis(days=30)
        
        assert "total_cost" in analysis
        assert analysis["total_cost"] > 0
        assert "daily_average" in analysis
        assert "trend" in analysis
        assert len(analysis["top_cost_services"]) > 0
    
    def test_get_cost_recommendations(self):
        """Test getting cost recommendations."""
        analyzer = CostAnalyzer()
        
        # Record high costs
        for i in range(10):
            analyzer.record_cost(
                service="expensive-service",
                cost=2000.0,
                timestamp=datetime.now() - timedelta(days=i),
            )
        
        recommendations = analyzer.get_cost_recommendations()
        
        assert len(recommendations) > 0
        assert recommendations[0]["service"] == "expensive-service"