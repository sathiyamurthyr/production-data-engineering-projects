"""Tests for automation components."""

import pytest
from datetime import datetime, timedelta

from automation.auto_healer import (
    AutoHealer,
    SelfHealingPipeline,
    HealthChecker,
    HealthStatus,
    Issue,
    HealingStrategy,
    HealingResult,
)


class TestAutoHealer:
    """Test auto-healer."""
    
    def test_register_strategy(self):
        """Test registering healing strategy."""
        healer = AutoHealer()
        
        strategy = HealingStrategy(
            strategy_id="test-strategy",
            component="test-component",
            issue_type="test-issue",
            description="Test strategy",
            action="restart",
            max_attempts=3,
            cooldown_minutes=5,
        )
        
        healer.register_strategy(strategy)
        
        assert "test-strategy" in healer.strategies
    
    def test_detect_issue(self):
        """Test detecting issue."""
        healer = AutoHealer()
        
        issue = healer.detect_issue(
            component="test-component",
            issue_type="test-issue",
            description="Test issue",
            severity="high",
        )
        
        assert issue.issue_id is not None
        assert issue.component == "test-component"
        assert issue.resolved is False
        assert "test-component" in healer.component_health
        assert healer.component_health["test-component"] == HealthStatus.UNHEALTHY
    
    def test_detect_issue_with_strategy(self):
        """Test detecting issue with matching strategy."""
        healer = AutoHealer()
        
        # Register strategy
        strategy = HealingStrategy(
            strategy_id="restart",
            component="test-component",
            issue_type="test-issue",
            description="Restart",
            action="restart",
        )
        healer.register_strategy(strategy)
        
        # Detect issue - should auto-heal
        issue = healer.detect_issue(
            component="test-component",
            issue_type="test-issue",
            description="Test",
            severity="high",
        )
        
        assert issue.resolved is True
        assert healer.component_health["test-component"] == HealthStatus.HEALTHY
        assert len(healer.healing_history) == 1
    
    def test_detect_issue_no_strategy(self):
        """Test detecting issue without strategy."""
        healer = AutoHealer()
        
        issue = healer.detect_issue(
            component="unknown-component",
            issue_type="unknown-issue",
            description="Test",
            severity="high",
        )
        
        assert issue.resolved is False
        assert healer.component_health["unknown-component"] == HealthStatus.UNHEALTHY
    
    def test_cooldown_period(self):
        """Test healing cooldown period."""
        healer = AutoHealer()
        
        strategy = HealingStrategy(
            strategy_id="test",
            component="comp",
            issue_type="issue",
            description="Test",
            action="restart",
            cooldown_minutes=5,
        )
        healer.register_strategy(strategy)
        
        # First healing
        issue1 = healer.detect_issue("comp", "issue", "Test 1", "high")
        assert issue1.resolved is True
        
        # Immediate second healing - should be blocked by cooldown
        issue2 = healer.detect_issue("comp", "issue", "Test 2", "high")
        assert issue2.resolved is False
    
    def test_get_health_status(self):
        """Test getting health status."""
        healer = AutoHealer()
        
        healer.component_health["comp1"] = HealthStatus.HEALTHY
        healer.component_health["comp2"] = HealthStatus.UNHEALTHY
        
        status = healer.get_health_status()
        
        assert status["comp1"] == "healthy"
        assert status["comp2"] == "unhealthy"
    
    def test_get_healing_stats(self):
        """Test getting healing statistics."""
        healer = AutoHealer()
        
        # Register strategy and create issues
        strategy = HealingStrategy(
            strategy_id="test",
            component="comp",
            issue_type="issue",
            description="Test",
            action="restart",
        )
        healer.register_strategy(strategy)
        
        healer.detect_issue("comp", "issue", "Test 1", "high")
        healer.detect_issue("comp", "issue", "Test 2", "high")
        
        stats = healer.get_healing_stats()
        
        assert stats["total_attempts"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0


class TestSelfHealingPipeline:
    """Test self-healing pipeline."""
    
    def test_register_pipeline_health(self):
        """Test registering pipeline health check."""
        healer = AutoHealer()
        pipeline = SelfHealingPipeline(healer)
        
        def health_check():
            return True
        
        strategies = [
            HealingStrategy(
                strategy_id="restart",
                component="pipeline-1",
                issue_type="failure",
                description="Restart",
                action="restart",
            )
        ]
        
        pipeline.register_pipeline_health("pipeline-1", health_check, strategies)
        
        assert "pipeline-1" in pipeline.pipeline_status
    
    def test_check_pipeline_health(self):
        """Test checking pipeline health."""
        healer = AutoHealer()
        pipeline = SelfHealingPipeline(healer)
        
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        pipeline.register_pipeline_health("healthy-pipeline", healthy_check, [])
        pipeline.register_pipeline_health("unhealthy-pipeline", unhealthy_check, [])
        
        healthy_result = pipeline.check_pipeline_health("healthy-pipeline")
        unhealthy_result = pipeline.check_pipeline_health("unhealthy-pipeline")
        
        assert healthy_result["status"] == "healthy"
        assert unhealthy_result["status"] == "unhealthy"
    
    def test_heal_pipeline(self):
        """Test healing pipeline."""
        healer = AutoHealer()
        pipeline = SelfHealingPipeline(healer)
        
        strategy = HealingStrategy(
            strategy_id="restart",
            component="pipeline-1",
            issue_type="failure",
            description="Restart",
            action="restart",
        )
        
        def unhealthy_check():
            return False
        
        pipeline.register_pipeline_health("pipeline-1", unhealthy_check, [strategy])
        
        # First check - should be unhealthy
        pipeline.check_pipeline_health("pipeline-1")
        
        # Heal
        result = pipeline.heal_pipeline("pipeline-1")
        
        assert result["pipeline_id"] == "pipeline-1"
        assert "issue_id" in result


class TestHealthChecker:
    """Test health checker."""
    
    def test_register_check(self):
        """Test registering health check."""
        checker = HealthChecker()
        
        def check():
            return True
        
        checker.register_check("component-1", check)
        
        assert "component-1" in checker.checks
    
    def test_run_checks(self):
        """Test running health checks."""
        checker = HealthChecker()
        
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        checker.register_check("healthy", healthy_check)
        checker.register_check("unhealthy", unhealthy_check)
        
        results = checker.run_checks()
        
        assert results["healthy"]["healthy"] is True
        assert results["unhealthy"]["healthy"] is False
        assert "execution_time_ms" in results["healthy"]
    
    def test_get_overall_health(self):
        """Test getting overall health."""
        checker = HealthChecker()
        
        def check():
            return True
        
        checker.register_check("comp", check)
        checker.run_checks()
        
        health = checker.get_overall_health()
        
        assert health["status"] == "healthy"
        assert "components" in health
    
    def test_get_overall_health_no_results(self):
        """Test getting overall health with no results."""
        checker = HealthChecker()
        
        health = checker.get_overall_health()
        
        assert health["status"] == "unknown"