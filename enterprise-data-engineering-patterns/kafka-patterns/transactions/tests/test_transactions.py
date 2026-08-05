"""Unit tests for the Transactions Concepts pattern."""

import pytest

from src.transactions import Transactions, TransactionsConfig


class TestTransactionsConfig:
    """Tests for TransactionsConfig."""

    def test_default_config(self) -> None:
        config = TransactionsConfig()
        assert config.pattern_name == "transactions"


class TestTransactions:
    """Tests for Transactions."""

    def test_init_default_config(self) -> None:
        pattern = Transactions()
        assert pattern.config.pattern_name == "transactions"

    def test_init_custom_config(self) -> None:
        config = TransactionsConfig()
        pattern = Transactions(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Transactions()
        result = pattern.execute("test_data")
        assert result == "test_data"
