"""
Tests for Identity Services
Authentication, Authorization, RBAC
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from identity.authentication import AuthenticationService, AuthMethod, UserStatus
from identity.authorization import AuthorizationService, Effect, Action, Policy
from identity.rbac import RBACManager, PermissionType


@pytest.fixture
def auth_service():
    """Create authentication service"""
    return AuthenticationService(secret_key="test-secret-key")


@pytest.fixture
def authz_service():
    """Create authorization service"""
    return AuthorizationService()


@pytest.fixture
def rbac_manager(authz_service):
    """Create RBAC manager"""
    return RBACManager(authz_service)


@pytest.mark.asyncio
async def test_user_creation(auth_service):
    """Test user creation"""
    user = await auth_service.create_user(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        roles=["data-engineer"]
    )

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.status == UserStatus.ACTIVE
    assert "data-engineer" in user.roles
    assert user.failed_login_attempts == 0


@pytest.mark.asyncio
async def test_authentication_success(auth_service):
    """Test successful authentication"""
    # Create user
    await auth_service.create_user(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        roles=["data-engineer"]
    )

    # Authenticate
    token = await auth_service.authenticate(
        username="testuser",
        password="SecurePass123!"
    )

    assert token is not None
    assert token.access_token is not None
    assert token.refresh_token is not None
    assert token.scope == ["data-engineer"]


@pytest.mark.asyncio
async def test_authentication_failure(auth_service):
    """Test authentication failure"""
    # Create user
    await auth_service.create_user(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        roles=["data-engineer"]
    )

    # Authenticate with wrong password
    token = await auth_service.authenticate(
        username="testuser",
        password="WrongPassword"
    )

    assert token is None


@pytest.mark.asyncio
async def test_token_validation(auth_service):
    """Test token validation"""
    # Create user and authenticate
    await auth_service.create_user(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        roles=["data-engineer"]
    )

    token = await auth_service.authenticate(
        username="testuser",
        password="SecurePass123!"
    )

    # Validate token
    username = await auth_service.validate_token(token.access_token)
    assert username == "testuser"


@pytest.mark.asyncio
async def test_policy_creation(authz_service):
    """Test policy creation"""
    policy = Policy(
        policy_id="test-policy",
        name="Test Policy",
        description="Test policy description",
        effect=Effect.ALLOW,
        resources=["data-lake-*"],
        actions=[Action.READ, Action.WRITE],
        conditions={"department": "data"},
        priority=10,
        enabled=True,
        created_at=datetime.utcnow()
    )

    created = await authz_service.create_policy(policy)
    assert created.policy_id == "test-policy"
    assert created.effect == Effect.ALLOW


@pytest.mark.asyncio
async def test_access_check(authz_service):
    """Test access check"""
    # Create policy
    policy = Policy(
        policy_id="test-policy",
        name="Test Policy",
        description="Test policy description",
        effect=Effect.ALLOW,
        resources=["data-lake-*"],
        actions=[Action.READ],
        conditions={},
        priority=10,
        enabled=True,
        created_at=datetime.utcnow()
    )

    await authz_service.create_policy(policy)

    # Grant permission
    await authz_service.grant_role("data-engineer", ["data-lake:*:read"])

    # Check permission
    has_permission = await authz_service.check_permission("data-engineer", "data-lake:*:read")
    assert has_permission is True


@pytest.mark.asyncio
async def test_role_creation(rbac_manager):
    """Test role creation"""
    role = await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read", "data-lake:write", "airflow:read"]
    )

    assert role.role_id == "data-engineer"
    assert len(role.permissions) == 3
    assert "data-lake:read" in role.permissions


@pytest.mark.asyncio
async def test_role_assignment(rbac_manager):
    """Test role assignment"""
    # Create role
    await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read"]
    )

    # Assign role to user
    assignment = await rbac_manager.assign_role_to_user(
        user_id="user123",
        role_id="data-engineer",
        assigned_by="admin",
        justification="Team member onboarding"
    )

    assert assignment.user_id == "user123"
    assert assignment.role_id == "data-engineer"
    assert assignment.assigned_by == "admin"


@pytest.mark.asyncio
async def test_user_permissions(rbac_manager):
    """Test getting user permissions"""
    # Create role with permissions
    await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read", "data-lake:write", "kafka:read"]
    )

    # Assign role
    await rbac_manager.assign_role_to_user(
        user_id="user123",
        role_id="data-engineer",
        assigned_by="admin",
        justification="Onboarding"
    )

    # Get user permissions
    permissions = await rbac_manager.get_user_permissions("user123")

    assert len(permissions) == 3
    assert "data-lake:read" in permissions
    assert "data-lake:write" in permissions
    assert "kafka:read" in permissions


@pytest.mark.asyncio
async def test_permission_check(rbac_manager):
    """Test permission check"""
    # Create role
    await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read"]
    )

    # Assign role
    await rbac_manager.assign_role_to_user(
        user_id="user123",
        role_id="data-engineer",
        assigned_by="admin",
        justification="Onboarding"
    )

    # Check permission
    has_permission = await rbac_manager.check_permission("user123", "data-lake:read")
    assert has_permission is True

    has_permission = await rbac_manager.check_permission("user123", "data-lake:write")
    assert has_permission is False


@pytest.mark.asyncio
async def test_role_revocation(rbac_manager):
    """Test role revocation"""
    # Create and assign role
    await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read"]
    )

    await rbac_manager.assign_role_to_user(
        user_id="user123",
        role_id="data-engineer",
        assigned_by="admin",
        justification="Onboarding"
    )

    # Verify assignment
    permissions = await rbac_manager.get_user_permissions("user123")
    assert len(permissions) == 1

    # Revoke role
    await rbac_manager.revoke_role("user123", "data-engineer")

    # Verify revocation
    permissions = await rbac_manager.get_user_permissions("user123")
    assert len(permissions) == 0


@pytest.mark.asyncio
async def test_role_hierarchy(rbac_manager):
    """Test role hierarchy"""
    # Create parent role
    await rbac_manager.create_role(
        role_id="admin",
        name="Administrator",
        description="System administrator",
        permissions=["*:*"]
    )

    # Create child role
    await rbac_manager.create_role(
        role_id="super-user",
        name="Super User",
        description="Super user with inherited permissions",
        permissions=["data-lake:write"]
    )

    # Create hierarchy
    await rbac_manager.create_role_hierarchy("admin", "super-user")

    # Assign child role
    await rbac_manager.assign_role_to_user(
        user_id="user123",
        role_id="super-user",
        assigned_by="admin",
        justification="Elevated permissions"
    )

    # Get inherited roles
    roles = await rbac_manager.get_user_roles("user123")
    role_ids = [r.role_id for r in roles]

    assert "super-user" in role_ids
    assert "admin" in role_ids  # Inherited


@pytest.mark.asyncio
async def test_add_permission_to_role(rbac_manager):
    """Test adding permission to role"""
    # Create role
    await rbac_manager.create_role(
        role_id="data-engineer",
        name="Data Engineer",
        description="Data engineering team member",
        permissions=["data-lake:read"]
    )

    # Add permission
    await rbac_manager.add_permission_to_role("data-engineer", "kafka:read")

    # Verify
    permissions = await rbac_manager.get_user_permissions("user123")
    # Note: This test assumes user has the role assigned