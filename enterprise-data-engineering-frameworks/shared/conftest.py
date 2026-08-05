"""Shared pytest fixtures."""
from __future__ import annotations
import pytest


@pytest.fixture
def tmp_config_file(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("name: test\nversion: 1.0\n")
    return config


@pytest.fixture
def sample_data():
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "active": True},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": False},
    ]

