"""Tests for disaster recovery components."""

import pytest
from datetime import datetime, timedelta

from dr.backup_manager import (
    BackupManager,
    RecoveryEngine,
    FailoverCoordinator,
    RecoveryTimeEstimator,
    BackupStatus,
    BackupType,
)


class TestBackupManager:
    """Test backup manager."""
    
    def test_schedule_backup(self):
        """Test scheduling backup."""
        manager = BackupManager()
        
        schedule = manager.schedule_backup(
            source="database",
            backup_type="full",
            schedule_cron="0 0 * * *",
            retention_days=30,
        )
        
        assert schedule["source"] == "database"
        assert schedule["backup_type"] == "full"
        assert schedule["enabled"] is True
    
    def test_create_backup(self):
        """Test creating backup."""
        manager = BackupManager()
        
        backup = manager.create_backup(
            source="database",
            backup_type="full",
            destination="s3://bucket/backup",
        )
        
        assert backup.backup_id is not None
        assert backup.source == "database"
        assert backup.status == "completed"
        assert backup.size_bytes > 0
    
    def test_validate_backup(self):
        """Test validating backup."""
        manager = BackupManager()
        
        backup = manager.create_backup("db", "full", "s3://bucket")
        validation = manager.validate_backup(backup.backup_id)
        
        assert validation["valid"] is True
        assert validation["checksum"] is True
    
    def test_validate_nonexistent_backup(self):
        """Test validating non-existent backup."""
        manager = BackupManager()
        
        validation = manager.validate_backup("BKP-NONEXISTENT")
        
        assert validation["valid"] is False
        assert "error" in validation
    
    def test_get_recovery_point(self):
        """Test getting recovery point."""
        manager = BackupManager()
        
        # Create backups at different times
        backup1 = manager.create_backup("db", "full", "s3://bucket")
        backup2 = manager.create_backup("db", "full", "s3://bucket")
        
        # Get recovery point
        target_time = datetime.now() - timedelta(minutes=5)
        recovery_point = manager.get_recovery_point(target_time)
        
        # Should return the most recent backup
        assert recovery_point is not None
        assert recovery_point.backup_id == backup2.backup_id
    
    def test_get_backup_status(self):
        """Test getting backup status."""
        manager = BackupManager()
        
        # Create some backups
        for i in range(5):
            manager.create_backup("db", "full", "s3://bucket")
        
        status = manager.get_backup_status()
        
        assert status["total_backups"] == 5
        assert status["completed"] == 5
        assert status["recovery_points"] == 5


class TestRecoveryEngine:
    """Test recovery engine."""
    
    def test_initiate_recovery(self):
        """Test initiating recovery."""
        backup_mgr = BackupManager()
        recovery_engine = RecoveryEngine(backup_mgr)
        
        # Create a backup first
        backup = backup_mgr.create_backup("db", "full", "s3://bucket")
        
        # Initiate recovery
        plan = recovery_engine.initiate_recovery(
            source="database",
            target_timestamp=datetime.now(),
            target_environment="dr-region",
        )
        
        assert "recovery_id" in plan
        assert plan["target_environment"] == "dr-region"
        assert len(plan["steps"]) > 0
    
    def test_initiate_recovery_no_backup(self):
        """Test initiating recovery with no backup."""
        backup_mgr = BackupManager()
        recovery_engine = RecoveryEngine(backup_mgr)
        
        plan = recovery_engine.initiate_recovery(
            source="database",
            target_timestamp=datetime.now() - timedelta(days=365),
            target_environment="dr-region",
        )
        
        assert "error" in plan
        assert plan.get("success") is False
    
    def test_execute_recovery(self):
        """Test executing recovery."""
        backup_mgr = BackupManager()
        recovery_engine = RecoveryEngine(backup_mgr)
        
        backup = backup_mgr.create_backup("db", "full", "s3://bucket")
        plan = recovery_engine.initiate_recovery("database", datetime.now(), "dr")
        
        result = recovery_engine.execute_recovery(plan)
        
        assert result["success"] is True
        assert "duration_minutes" in result


class TestFailoverCoordinator:
    """Test failover coordinator."""
    
    def test_check_health_primary(self):
        """Test checking primary region health."""
        coordinator = FailoverCoordinator()
        
        health = coordinator.check_health("us-east-1")
        
        assert health["region"] == "us-east-1"
        assert "healthy" in health
        assert "checks" in health
    
    def test_initiate_failover(self):
        """Test initiating failover."""
        coordinator = FailoverCoordinator()
        
        result = coordinator.initiate_failover("us-west-2")
        
        assert result["success"] is True
        assert result["current_region"] == "us-west-2"
    
    def test_initiate_failover_invalid_region(self):
        """Test initiating failover to invalid region."""
        coordinator = FailoverCoordinator()
        
        result = coordinator.initiate_failover("invalid-region")
        
        assert result["success"] is False
        assert "error" in result


class TestRecoveryTimeEstimator:
    """Test recovery time estimator."""
    
    def test_estimate_recovery_time_database(self):
        """Test estimating database recovery time."""
        estimator = RecoveryTimeEstimator()
        
        result = estimator.estimate_recovery_time("database", "medium")
        
        assert "estimated_minutes" in result
        assert "estimated_with_buffer" in result
        assert result["rto_target"] >= result["estimated_minutes"]
    
    def test_estimate_recovery_time_pipeline(self):
        """Test estimating pipeline recovery time."""
        estimator = RecoveryTimeEstimator()
        
        result = estimator.estimate_recovery_time("pipeline", "low")
        
        assert result["estimated_minutes"] > 0
        assert result["complexity"] == "low"
    
    def test_estimate_different_complexities(self):
        """Test estimating with different complexities."""
        estimator = RecoveryTimeEstimator()
        
        low = estimator.estimate_recovery_time("service", "low")
        medium = estimator.estimate_recovery_time("service", "medium")
        high = estimator.estimate_recovery_time("service", "high")
        
        assert low["estimated_minutes"] < medium["estimated_minutes"]
        assert medium["estimated_minutes"] < high["estimated_minutes"]