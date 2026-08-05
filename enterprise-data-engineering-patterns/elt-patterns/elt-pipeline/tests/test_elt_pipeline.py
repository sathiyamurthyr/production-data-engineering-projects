"""Unit tests for the ELT Pipeline pattern."""

import pytest

from src.elt_pipeline import EltPipeline, EltPipelineConfig


class TestEltPipelineConfig:
    """Tests for EltPipelineConfig."""

    def test_default_config(self) -> None:
        config = EltPipelineConfig()
        assert config.pattern_name == "elt-pipeline"


class TestEltPipeline:
    """Tests for EltPipeline."""

    def test_init_default_config(self) -> None:
        pattern = EltPipeline()
        assert pattern.config.pattern_name == "elt-pipeline"

    def test_init_custom_config(self) -> None:
        config = EltPipelineConfig()
        pattern = EltPipeline(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = EltPipeline()
        result = pattern.execute("test_data")
        assert result == "test_data"
