"""Unit tests for the API Pagination pattern."""

import pytest

from src.api_pagination import ApiPagination, ApiPaginationConfig


class TestApiPaginationConfig:
    """Tests for ApiPaginationConfig."""

    def test_default_config(self) -> None:
        config = ApiPaginationConfig()
        assert config.pattern_name == "api-pagination"


class TestApiPagination:
    """Tests for ApiPagination."""

    def test_init_default_config(self) -> None:
        pattern = ApiPagination()
        assert pattern.config.pattern_name == "api-pagination"

    def test_init_custom_config(self) -> None:
        config = ApiPaginationConfig()
        pattern = ApiPagination(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ApiPagination()
        result = pattern.execute("test_data")
        assert result == "test_data"
