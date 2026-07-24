"""Pytest configuration and shared fixtures."""
import pytest


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {"environment": "test", "batch_size": 100}
