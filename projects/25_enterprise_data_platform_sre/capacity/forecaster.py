"""Capacity Planning & Load Forecasting."""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MetricData(BaseModel):
    """Historical metric data point."""
    timestamp: datetime
    value: float
    metadata: dict[str, Any] = {}


class ForecastResult(BaseModel):
    """Forecast result."""
    metric_name: str
    predicted_values: list[float]
    confidence_upper: list[float]
    confidence_lower: list[float]
    forecast_dates: list[datetime]
    model_accuracy: float
    recommendations: list[str]


class ScalingRecommendation(BaseModel):
    """Scaling recommendation."""
    action: str  # scale_up, scale_down, maintain
    reason: str
    current_usage: float
    predicted_usage: float
    recommended_capacity: float
    urgency: str  # immediate, planned, monitor


class CapacityPlanner:
    """Capacity planning and forecasting for data platform."""
    
    def __init__(self):
        """Initialize capacity planner."""
        self.historical_data: dict[str, list[MetricData]] = {}
        self.forecast_models: dict[str, Any] = {}
    
    def load_historical_data(self, metric_name: str, data: list[MetricData]) -> None:
        """Load historical metric data.
        
        Args:
            metric_name: Metric name
            data: Historical data points
        """
        self.historical_data[metric_name] = data
        logger.info(f"Loaded {len(data)} historical data points for {metric_name}")
    
    def forecast_growth(
        self,
        metric_name: str,
        days_ahead: int = 30,
        confidence_level: float = 0.95,
    ) -> ForecastResult:
        """Forecast capacity needs.
        
        Args:
            metric_name: Metric to forecast
            days_ahead: Days to forecast
            confidence_level: Confidence level (0-1)
            
        Returns:
            Forecast result
        """
        data = self.historical_data.get(metric_name, [])
        
        if len(data) < 7:
            raise ValueError(f"Insufficient data for forecasting: {metric_name}")
        
        # Extract values and timestamps
        values = [d.value for d in data]
        timestamps = [d.timestamp for d in data]
        
        # Simple linear regression (actual implementation would use ARIMA, Prophet, etc.)
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        slope, intercept = coeffs[0], coeffs[1]
        
        # Generate forecast
        future_x = np.arange(len(values), len(values) + days_ahead)
        predicted = slope * future_x + intercept
        
        # Calculate confidence interval
        residuals = values - (slope * x + intercept)
        std_dev = np.std(residuals)
        z_score = 1.96  # 95% confidence
        
        confidence_margin = z_score * std_dev
        upper_bound = predicted + confidence_margin
        lower_bound = predicted - confidence_margin
        
        # Generate future dates
        last_date = timestamps[-1]
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(days_ahead)]
        
        # Calculate accuracy on historical data
        fitted_values = slope * x + intercept
        mape = np.mean(np.abs((values - fitted_values) / values)) * 100
        accuracy = max(0, 100 - mape)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            metric_name,
            predicted[-1],
            values[-1],
        )
        
        result = ForecastResult(
            metric_name=metric_name,
            predicted_values=predicted.tolist(),
            confidence_upper=upper_bound.tolist(),
            confidence_lower=lower_bound.tolist(),
            forecast_dates=forecast_dates,
            model_accuracy=accuracy,
            recommendations=recommendations,
        )
        
        logger.info(f"Forecast generated for {metric_name}: {days_ahead} days ahead")
        return result
    
    def recommend_scaling(
        self,
        metric_name: str,
        current_usage: float,
        max_capacity: float,
        forecast: ForecastResult = None,
    ) -> ScalingRecommendation:
        """Generate scaling recommendations.
        
        Args:
            metric_name: Metric name
            current_usage: Current usage
            max_capacity: Maximum capacity
            forecast: Forecast result
            
        Returns:
            Scaling recommendation
        """
        if forecast is None:
            forecast = self.forecast_growth(metric_name)
        
        predicted_peak = max(forecast.predicted_values)
        utilization_pct = (current_usage / max_capacity) * 100 if max_capacity > 0 else 0
        predicted_utilization = (predicted_peak / max_capacity) * 100 if max_capacity > 0 else 0
        
        # Determine action
        if predicted_utilization > 80:
            action = "scale_up"
            urgency = "immediate" if predicted_utilization > 90 else "planned"
            reason = f"Predicted utilization {predicted_utilization:.1f}% exceeds 80% threshold"
            recommended_capacity = predicted_peak * 1.5
        elif predicted_utilization < 30 and utilization_pct < 50:
            action = "scale_down"
            urgency = "planned"
            reason = f"Predicted utilization {predicted_utilization:.1f}% below 30% threshold"
            recommended_capacity = predicted_peak * 1.2
        else:
            action = "maintain"
            urgency = "monitor"
            reason = f"Utilization within acceptable range: {predicted_utilization:.1f}%"
            recommended_capacity = max_capacity
        
        return ScalingRecommendation(
            action=action,
            reason=reason,
            current_usage=current_usage,
            predicted_usage=predicted_peak,
            recommended_capacity=recommended_capacity,
            urgency=urgency,
        )
    
    def _generate_recommendations(
        self,
        metric_name: str,
        predicted_value: float,
        current_value: float,
    ) -> list[str]:
        """Generate recommendations based on forecast.
        
        Args:
            metric_name: Metric name
            predicted_value: Predicted value
            current_value: Current value
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        growth_rate = ((predicted_value - current_value) / current_value * 100) if current_value > 0 else 0
        
        if growth_rate > 50:
            recommendations.append(
                f"Significant growth predicted ({growth_rate:.1f}%). Consider proactive scaling."
            )
        elif growth_rate > 20:
            recommendations.append(
                f"Moderate growth predicted ({growth_rate:.1f}%). Monitor closely and plan scaling."
            )
        elif growth_rate < -20:
            recommendations.append(
                f"Decline predicted ({growth_rate:.1f}%). Consider cost optimization."
            )
        
        if not recommendations:
            recommendations.append("Stable workload expected. Maintain current capacity.")
        
        return recommendations


class CapacityOptimizer:
    """Optimize resource allocation."""
    
    def __init__(self):
        """Initialize capacity optimizer."""
        self.resources: dict[str, dict[str, Any]] = {}
        self.optimization_history: list[dict[str, Any]] = []
    
    def register_resource(
        self,
        resource_name: str,
        current_capacity: float,
        utilization: float,
        cost_per_unit: float,
    ) -> None:
        """Register resource for optimization.
        
        Args:
            resource_name: Resource name
            current_capacity: Current capacity
            utilization: Current utilization (0-100)
            cost_per_unit: Cost per unit capacity
        """
        self.resources[resource_name] = {
            "current_capacity": current_capacity,
            "utilization": utilization,
            "cost_per_unit": cost_per_unit,
            "total_cost": current_capacity * cost_per_unit,
        }
    
    def optimize(self) -> dict[str, Any]:
        """Optimize resource allocation.
        
        Returns:
            Optimization recommendations
        """
        recommendations = []
        total_savings = 0.0
        
        for resource_name, resource in self.resources.items():
            utilization = resource["utilization"]
            
            if utilization < 30:
                # Underutilized - recommend downsizing
                recommended_capacity = resource["current_capacity"] * 0.7
                savings = (resource["current_capacity"] - recommended_capacity) * resource["cost_per_unit"]
                
                recommendations.append({
                    "resource": resource_name,
                    "action": "scale_down",
                    "current_capacity": resource["current_capacity"],
                    "recommended_capacity": recommended_capacity,
                    "estimated_savings": savings,
                    "reason": f"Low utilization: {utilization:.1f}%",
                })
                
                total_savings += savings
            
            elif utilization > 80:
                # Overutilized - recommend upsizing
                recommended_capacity = resource["current_capacity"] * 1.5
                additional_cost = (recommended_capacity - resource["current_capacity"]) * resource["cost_per_unit"]
                
                recommendations.append({
                    "resource": resource_name,
                    "action": "scale_up",
                    "current_capacity": resource["current_capacity"],
                    "recommended_capacity": recommended_capacity,
                    "additional_cost": additional_cost,
                    "reason": f"High utilization: {utilization:.1f}%",
                })
        
        result = {
            "recommendations": recommendations,
            "total_monthly_savings": total_savings,
            "optimization_count": len(recommendations),
        }
        
        self.optimization_history.append(result)
        return result


class CostAnalyzer:
    """Analyze and optimize platform costs."""
    
    def __init__(self):
        """Initialize cost analyzer."""
        self.cost_data: dict[str, list[dict[str, Any]]] = {}
    
    def record_cost(
        self,
        service: str,
        cost: float,
        timestamp: datetime,
        metadata: dict[str, Any] = None,
    ) -> None:
        """Record cost data.
        
        Args:
            service: Service name
            cost: Cost amount
            timestamp: Timestamp
            metadata: Additional metadata
        """
        if service not in self.cost_data:
            self.cost_data[service] = []
        
        self.cost_data[service].append({
            "cost": cost,
            "timestamp": timestamp,
            "metadata": metadata or {},
        })
    
    def get_cost_analysis(self, days: int = 30) -> dict[str, Any]:
        """Get cost analysis.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Cost analysis
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        analysis = {
            "total_cost": 0.0,
            "cost_by_service": {},
            "daily_average": 0.0,
            "trend": "stable",
            "top_cost_services": [],
        }
        
        service_costs = {}
        
        for service, records in self.cost_data.items():
            # Filter by date
            service_records = [r for r in records if r["timestamp"] > cutoff]
            
            # Calculate total
            total = sum(r["cost"] for r in service_records)
            service_costs[service] = total
            analysis["total_cost"] += total
        
        # Calculate daily average
        analysis["daily_average"] = analysis["total_cost"] / days if days > 0 else 0
        
        # Sort by cost
        sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        analysis["top_cost_services"] = [
            {"service": s, "cost": c}
            for s, c in sorted_services[:10]
        ]
        
        # Calculate trend
        if len(self.cost_data) > 1:
            recent = sum(
                r["cost"]
                for service, records in self.cost_data.items()
                for r in records
                if r["timestamp"] > datetime.now() - timedelta(days=7)
            )
            older = sum(
                r["cost"]
                for service, records in self.cost_data.items()
                for r in records
                if timedelta(days=7) < r["timestamp"] < timedelta(days=14)
            )
            
            if recent > older * 1.2:
                analysis["trend"] = "increasing"
            elif recent < older * 0.8:
                analysis["trend"] = "decreasing"
        
        analysis["cost_by_service"] = service_costs
        
        return analysis
    
    def get_cost_recommendations(self) -> list[dict[str, Any]]:
        """Get cost optimization recommendations.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze each service
        for service, records in self.cost_data.items():
            if not records:
                continue
            
            # Calculate average daily cost
            total_cost = sum(r["cost"] for r in records)
            avg_daily = total_cost / len(records) if records else 0
            
            if avg_daily > 1000:
                recommendations.append({
                    "service": service,
                    "action": "review_usage",
                    "reason": f"High daily cost: ${avg_daily:.2f}",
                    "potential_savings": avg_daily * 0.2,  # 20% savings estimate
                })
        
        return recommendations