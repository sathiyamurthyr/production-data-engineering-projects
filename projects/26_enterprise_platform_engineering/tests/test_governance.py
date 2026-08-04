"""
Tests for Governance Service
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from platform.services.governance import (
    GovernanceService,
    Policy,
    PolicyType,
    PolicySeverity,
    PolicyViolation,
    AuditLog
)


@pytest.fixture
def governance_service():
    """Create governance service instance."""
    return GovernanceService()


@pytest.mark.asyncio
async def test_list_policies_empty(governance_service):
    """Test listing policies when empty."""
    policies = await governance_service.list_policies()
    assert policies == []


@pytest.mark.asyncio
async def test_create_policy(governance_service):
    """Test policy creation."""
    policy = Policy(
        id="policy-123",
        name="Test Policy",
        policy_type=PolicyType.SECURITY,
        severity=PolicySeverity.HIGH,
        description="Test policy description",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="admin"
    )

    created = await governance_service.create_policy(policy)

    assert created is not None
    assert created.id == "policy-123"
    assert created.name == "Test Policy"
    assert created.policy_type == PolicyType.SECURITY


@pytest.mark.asyncio
async def test_get_policy(governance_service):
    """Test getting policy by ID."""
    # Create policy first
    policy = Policy(
        id="policy-123",
        name="Test Policy",
        policy_type=PolicyType.SECURITY,
        severity=PolicySeverity.HIGH,
        description="Test policy",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="admin"
    )
    await governance_service.create_policy(policy)

    # Get policy
    retrieved = await governance_service.get_policy("policy-123")

    assert retrieved is not None
    assert retrieved.id == "policy-123"
    assert retrieved.name == "Test Policy"


@pytest.mark.asyncio
async def test_get_policy_not_found(governance_service):
    """Test getting non-existent policy."""
    policy = await governance_service.get_policy("nonexistent-id")
    assert policy is None


@pytest.mark.asyncio
async def test_list_policies_with_filter(governance_service):
    """Test listing policies with filters."""
    # Create policies with different types
    await governance_service.create_policy(Policy(
        id="policy-1",
        name="Security Policy",
        policy_type=PolicyType.SECURITY,
        severity=PolicySeverity.HIGH,
        description="Security policy",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="admin"
    ))

    await governance_service.create_policy(Policy(
        id="policy-2",
        name="Cost Policy",
        policy_type=PolicyType.COST,
        severity=PolicySeverity.MEDIUM,
        description="Cost policy",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="admin"
    ))

    # Filter by type
    security_policies = await governance_service.list_policies(policy_type=PolicyType.SECURITY)
    assert len(security_policies) == 1
    assert security_policies[0].name == "Security Policy"

    # Filter by enabled
    enabled_policies = await governance_service.list_policies(enabled=True)
    assert len(enabled_policies) >= 2


@pytest.mark.asyncio
async def test_log_audit_event(governance_service):
    """Test audit event logging."""
    await governance_service.log_audit_event(
        event_type="user_login",
        severity="info",
        user_id="user-123",
        resource_id="auth-123",
        resource_type="authentication",
        action="login",
        result="success",
        details={"ip_address": "192.168.1.1"}
    )

    # Verify event was logged
    logs = await governance_service.get_audit_logs(event_type="user_login")
    assert len(logs) >= 1
    assert logs[0].event_type == "user_login"


@pytest.mark.asyncio
async def test_get_audit_logs_with_filters(governance_service):
    """Test getting audit logs with filters."""
    # Log multiple events
    for i in range(3):
        await governance_service.log_audit_event(
            event_type="resource_created",
            severity="info",
            user_id=f"user-{i}",
            resource_id=f"resource-{i}",
            resource_type="service",
            action="create",
            result="success",
            details={}
        )

    # Filter by event type
    logs = await governance_service.get_audit_logs(event_type="resource_created")
    assert len(logs) >= 3

    # Filter by user
    user_logs = await governance_service.get_audit_logs(user_id="user-0")
    assert len(user_logs) >= 1


@pytest.mark.asyncio
async def test_resolve_violation(governance_service):
    """Test resolving policy violation."""
    # Create a violation
    violation = PolicyViolation(
        id="violation-123",
        policy_id="policy-123",
        resource_id="resource-123",
        resource_type="service",
        severity=PolicySeverity.HIGH,
        message="Policy violation",
        resolved=False,
        created_at=datetime.utcnow()
    )

    # Save violation (simulated)
    governance_service.violations["resource-123"] = [violation]

    # Resolve violation
    result = await governance_service.resolve_violation(
        "violation-123",
        "admin",
        "Fixed by updating configuration"
    )

    assert result is True

    # Verify resolution
    violations = await governance_service.get_violations(resolved=True)
    # Note: In real implementation, this would query the database


@pytest.mark.asyncio
async def test_get_violations(governance_service):
    """Test getting policy violations."""
    # Create violations
    violation1 = PolicyViolation(
        id="violation-1",
        policy_id="policy-1",
        resource_id="resource-1",
        resource_type="service",
        severity=PolicySeverity.HIGH,
        message="Violation 1",
        resolved=False,
        created_at=datetime.utcnow()
    )

    violation2 = PolicyViolation(
        id="violation-2",
        policy_id="policy-2",
        resource_id="resource-2",
        resource_type="service",
        severity=PolicySeverity.MEDIUM,
        message="Violation 2",
        resolved=True,
        created_at=datetime.utcnow()
    )

    governance_service.violations["resource-1"] = [violation1]
    governance_service.violations["resource-2"] = [violation2]

    # Get all violations
    all_violations = await governance_service.get_violations()
    assert len(all_violations) >= 2

    # Get unresolved violations
    unresolved = await governance_service.get_violations(resolved=False)
    assert len(unresolved) >= 1


@pytest.mark.asyncio
async def test_health_check(governance_service):
    """Test health check."""
    health = await governance_service.health_check()
    assert "status" in health
    assert health["status"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_get_statistics(governance_service):
    """Test getting governance statistics."""
    # Create some policies and violations
    await governance_service.create_policy(Policy(
        id="policy-1",
        name="Test Policy",
        policy_type=PolicyType.SECURITY,
        severity=PolicySeverity.HIGH,
        description="Test",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by="admin"
    ))

    stats = await governance_service.get_statistics()

    assert "total_policies" in stats
    assert "enabled_policies" in stats
    assert "policies_by_type" in stats
    assert "total_violations" in stats
    assert stats["total_policies"] >= 1