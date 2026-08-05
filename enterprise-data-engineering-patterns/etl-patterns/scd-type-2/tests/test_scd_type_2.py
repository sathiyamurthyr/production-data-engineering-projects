"""Unit tests for the SCD Type 2 pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from scd_type_2 import (
    SCD2Config,
    SCD2TypeTwo,
    SCD2Pipeline,
    SCD2Record,
)


class TestSCD2Config:
    """Tests for SCD2Config."""

    def test_defaults(self) -> None:
        config = SCD2Config()
        assert config.pattern_name == "scd-type-2"
        assert config.effective_date_column == "effective_from"
        assert config.expiry_date_column == "effective_to"
        assert config.is_current_column == "is_current"
        assert config.default_expiry == "9999-12-31"

    def test_custom_business_key(self) -> None:
        config = SCD2Config(business_key_columns=["customer_id", "region"])
        assert config.business_key_columns == ["customer_id", "region"]


class TestSCD2Record:
    """Tests for SCD2Record model."""

    def test_close_record(self) -> None:
        record = SCD2Record(business_key="key1", data={}, surrogate_key=1)
        record.close_record()
        assert record.is_current is False
        assert record.effective_to != "9999-12-31 23:59:59"

    def test_compute_surrogate_key(self) -> None:
        from datetime import datetime, timezone
        record = SCD2Record(
            business_key="cust_1",
            data={},
            surrogate_key=0,
            effective_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        key = record.compute_surrogate_key()
        assert isinstance(key, int)
        assert key > 0


class TestSCD2TypeTwo:
    """Tests for SCD2TypeTwo core logic."""

    def test_compute_business_key_single_col(self) -> None:
        config = SCD2Config(business_key_columns=["id"])
        scd = SCD2TypeTwo(config)
        key = scd.compute_business_key({"id": 42, "name": "Alice"})
        assert key == "42"

    def test_compute_business_key_multi_col(self) -> None:
        config = SCD2Config(business_key_columns=["id", "region"])
        scd = SCD2TypeTwo(config)
        key = scd.compute_business_key({"id": 1, "region": "US", "val": 10})
        assert key == "1|US"

    def test_compute_data_hash(self) -> None:
        config = SCD2Config(tracked_columns=["name", "email"])
        scd = SCD2TypeTwo(config)
        h1 = scd.compute_data_hash({"name": "Alice", "email": "a@b.com"})
        h2 = scd.compute_data_hash({"name": "Alice", "email": "a@b.com"})
        assert h1 == h2

        h3 = scd.compute_data_hash({"name": "Bob", "email": "a@b.com"})
        assert h1 != h3

    def test_detect_changes_new_entity(self) -> None:
        config = SCD2Config(business_key_columns=["id"])
        scd = SCD2TypeTwo(config)
        changes = scd.detect_changes([], [{"id": 1, "name": "Alice"}])
        assert len(changes) == 1
        assert changes[0]["action"] == "INSERT"

    def test_detect_changes_update(self) -> None:
        config = SCD2Config(business_key_columns=["id"], tracked_columns=["name"])
        scd = SCD2TypeTwo(config)
        existing = [{"id": 1, "name": "Alice", "is_current": True}]
        incoming = [{"id": 1, "name": "Bob"}]
        changes = scd.detect_changes(existing, incoming)
        assert len(changes) == 1
        assert changes[0]["action"] == "UPDATE"

    def test_detect_changes_no_change(self) -> None:
        config = SCD2Config(business_key_columns=["id"], tracked_columns=["name"])
        scd = SCD2TypeTwo(config)
        existing = [{"id": 1, "name": "Alice", "is_current": True}]
        incoming = [{"id": 1, "name": "Alice"}]
        changes = scd.detect_changes(existing, incoming)
        assert len(changes) == 1
        assert changes[0]["action"] == "NO_CHANGE"

    def test_apply_changes_insert(self) -> None:
        config = SCD2Config(
            business_key_columns=["id"],
            surrogate_key_column="sk",
        )
        scd = SCD2TypeTwo(config)
        changes = [{"action": "INSERT", "business_key": "1", "data": {"id": 1, "name": "Alice"}}]
        result = scd.apply_changes(changes, [])
        assert len(result) == 1
        assert result[0]["is_current"] is True
        assert result[0]["version"] == 1
        assert result[0]["surrogate_key"] is not None

    def test_apply_changes_update_closes_old(self) -> None:
        config = SCD2Config(
            business_key_columns=["id"],
            surrogate_key_column="sk",
            is_current_column="is_current",
            expiry_date_column="effective_to",
        )
        scd = SCD2TypeTwo(config)
        existing = [{"id": 1, "name": "Alice", "is_current": True, "version": 1}]
        changes = [{"action": "UPDATE", "business_key": "1", "old_record": existing[0], "new_data": {"id": 1, "name": "Bob"}}]
        result = scd.apply_changes(changes, existing)
        assert len(result) == 2
        # Old record closed
        old = [r for r in result if r["name"] == "Alice"][0]
        assert old["is_current"] is False
        assert old["version"] == 1
        # New record current
        new = [r for r in result if r["name"] == "Bob"][0]
        assert new["is_current"] is True
        assert new["version"] == 2

    def test_get_current_records(self) -> None:
        config = SCD2Config(business_key_columns=["id"])
        scd = SCD2TypeTwo(config)
        records = [
            {"id": 1, "is_current": True},
            {"id": 2, "is_current": False},
            {"id": 3, "is_current": True},
        ]
        current = scd.get_current_records(records)
        assert len(current) == 2

    def test_get_history_for_key(self) -> None:
        config = SCD2Config(business_key_columns=["id"])
        scd = SCD2TypeTwo(config)
        records = [
            {"id": 1, "version": 1, "is_current": False},
            {"id": 1, "version": 2, "is_current": True},
            {"id": 2, "version": 1, "is_current": True},
        ]
        history = scd.get_history_for_key(records, "1")
        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[1]["version"] == 2


class TestSCD2Pipeline:
    """Tests for the end-to-end pipeline."""

    def test_full_pipeline_insert(self) -> None:
        config = SCD2Config(business_key_columns=["id"])
        pipeline = SCD2Pipeline(config)
        existing = []
        incoming = [{"id": 1, "name": "Alice", "is_current": True}]
        result = pipeline.run(existing, incoming)
        assert len(result) == 1
        assert result[0]["is_current"] is True

    def test_full_pipeline_update(self) -> None:
        config = SCD2Config(
            business_key_columns=["id"],
            tracked_columns=["name"],
        )
        pipeline = SCD2Pipeline(config)
        existing = [{"id": 1, "name": "Alice", "is_current": True, "version": 1}]
        incoming = [{"id": 1, "name": "Bob"}]
        result = pipeline.run(existing, incoming)
        assert len(result) == 2
        current = [r for r in result if r["is_current"]]
        assert len(current) == 1
        assert current[0]["name"] == "Bob"
        assert current[0]["version"] == 2

    def test_full_pipeline_no_change(self) -> None:
        config = SCD2Config(
            business_key_columns=["id"],
            tracked_columns=["name"],
        )
        pipeline = SCD2Pipeline(config)
        existing = [{"id": 1, "name": "Alice", "is_current": True, "version": 1}]
        incoming = [{"id": 1, "name": "Alice"}]
        result = pipeline.run(existing, incoming)
        assert len(result) == 1  # No new record added
