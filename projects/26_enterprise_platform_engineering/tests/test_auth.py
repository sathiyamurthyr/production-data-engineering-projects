"""
Tests for Authentication Service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from platform.auth import AuthenticationService, UserCreate, Token
from platform.models.responses import HealthResponse


@pytest.fixture
def auth_service():
    """Create authentication service instance."""
    return AuthenticationService()


@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service):
    """Test successful user authentication."""
    # Create test user
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        full_name="Test User"
    )
    created_user = await auth_service.create_user(user_create)

    # Authenticate
    authenticated = await auth_service.authenticate_user("testuser", "testpass123")

    assert authenticated is not None
    assert authenticated.username == "testuser"
    assert authenticated.email == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(auth_service):
    """Test authentication with wrong password."""
    # Create test user
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    await auth_service.create_user(user_create)

    # Try to authenticate with wrong password
    authenticated = await auth_service.authenticate_user("testuser", "wrongpass")

    assert authenticated is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found(auth_service):
    """Test authentication with non-existent user."""
    authenticated = await auth_service.authenticate_user("nonexistent", "password")

    assert authenticated is None


@pytest.mark.asyncio
async def test_create_access_token(auth_service):
    """Test JWT token creation."""
    data = {"sub": "testuser", "roles": ["user"]}
    token = auth_service.create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_verify_token_valid(auth_service):
    """Test token verification with valid token."""
    # Create user first
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    await auth_service.create_user(user_create)

    # Create token
    data = {"sub": "testuser", "roles": ["user"]}
    token = auth_service.create_access_token(data)

    # Verify token
    token_data = await auth_service.verify_token(token)

    assert token_data is not None
    assert token_data.username == "testuser"


@pytest.mark.asyncio
async def test_verify_token_invalid(auth_service):
    """Test token verification with invalid token."""
    token_data = await auth_service.verify_token("invalid_token")

    assert token_data is None


@pytest.mark.asyncio
async def test_get_user_by_username(auth_service):
    """Test getting user by username."""
    # Create test user
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    created_user = await auth_service.create_user(user_create)

    # Get user
    user = await auth_service.get_user_by_username("testuser")

    assert user is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(auth_service):
    """Test getting non-existent user."""
    user = await auth_service.get_user_by_username("nonexistent")

    assert user is None


@pytest.mark.asyncio
async def test_health_check(auth_service):
    """Test health check."""
    health = await auth_service.health_check()

    assert "status" in health
    assert health["status"] in ["healthy", "unhealthy"]