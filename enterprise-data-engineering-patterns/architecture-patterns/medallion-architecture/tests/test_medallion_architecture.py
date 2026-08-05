"""Unit tests for the Medallion Architecture pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medallion_architecture import (
    DataRecord,
    Layer,
    MedallionArchitecture,
    MedallionConfig,
    MedallionPipeline,
    BronzeToSilverConfig,
    SilverToGoldConfig,
)


class TestMedallionConfig:
    """Tests for MedallionConfig."""

    def test_default_config(self) -> None:
        config = MedallionConfig()
        assert config.pattern_name == "medallion-architecture"
        assert config.enable_lineage is True
        assert config.enable_quality_checks is True

    def test_custom_config(self) -> None:
        bronze = BronzeToSilverConfig(dedup_columns=["id"])
        silver = SilverToGoldConfig(group_by_columns=["category"])
        config = MedallionConfig(
            bronze_config=bronze,
            silver_config=silver,
            enable_lineage=False,
        )
        assert config.bronze_config.dedup_columns == ["id"]
        assert config.silver_config.group_by_columns == ["category"]
        assert config.enable_lineage is False


class TestDataRecord:
    """Tests for DataRecord."""

    def test_compute_checksum(self) -> None:
        record = DataRecord(data={"a": 1, "b": 2})
        checksum = record.compute_checksum()
        assert len(checksum) == 32  # MD5 hex digest
        assert checksum == record.compute_checksum()

    def test_defaults(self) -> None:
        record = DataRecord(data={"id": 1})
        assert record.source_table == ""
        assert record.partition == ""
        assert record.checksum == ""


class TestBronzeLayer:
    """Tests for Bronze layer operations."""

    def test_load_records(self) -> None:
        config = MedallionConfig()
        medallion = MedallionArchitecture(config)
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        bronze = medallion.bronze_layer.load(records, source="api")

        assert len(bronze) == 2
        assert bronze[0].data == {"id": 1, "name": "Alice"}
        assert bronze[0].source_table == "api"
        assert bronze[0].partition == "default"
        assert len(bronze[0].checksum) == 32

    def test_load_with_partition(self) -> None:
        medallion = MedallionArchitecture()
        records = [{"id": 1}]
        bronze = medallion.bronze_layer.load(
            records, source="api", partition="2024-01-01"
        )
        assert bronze[0].partition == "2024-01-01"


class TestSilverLayer:
    """Tests for Silver layer operations."""

    def test_transform_dedup_by_columns(self) -> None:
        config = MedallionConfig(
            bronze_config=BronzeToSilverConfig(
                dedup_columns=["id"],
                timestamp_column="ts",
            )
        )
        medallion = MedallionArchitecture(config)

        # Create bronze records with duplicate IDs
        bronze = list(medallion.bronze_layer.load(
            [
                {"id": 1, "name": "Alice", "ts": "2024-01-01"},
                {"id": 1, "name": "Alice Updated", "ts": "2024-01-02"},
                {"id": 2, "name": "Bob", "ts": "2024-01-01"},
            ],
            source="api",
        ))

        silver = medallion.silver_layer.transform(bronze)
        assert len(silver) == 2  # Two unique IDs
        # Latest timestamp should win
        alice = [r for r in silver if r.data["id"] == 1][0]
        assert alice.data["name"] == "Alice Updated"

    def test_transform_dedup_by_checksum(self) -> None:
        medallion = MedallionArchitecture()
        bronze = list(medallion.bronze_layer.load(
            [
                {"id": 1, "name": "Alice"},
                {"id": 1, "name": "Alice"},  # Exact duplicate
                {"id": 2, "name": "Bob"},
            ],
            source="api",
        ))

        silver = medallion.silver_layer.transform(bronze)
        assert len(silver) == 2

    def test_transform_drop_columns(self) -> None:
        config = MedallionConfig(
            bronze_config=BronzeToSilverConfig(drop_columns=["temp_col"])
        )
        medallion = MedallionArchitecture(config)
        bronze = list(medallion.bronze_layer.load(
            [{"id": 1, "temp_col": "junk", "name": "Alice"}],
            source="api",
        ))

        silver = medallion.silver_layer.transform(bronze)
        assert "temp_col" not in silver[0].data
        assert silver[0].data["name"] == "Alice"

    def test_quality_checks_null_filter(self) -> None:
        config = MedallionConfig(
            bronze_config=BronzeToSilverConfig(
                quality_checks=["not_null"]
            )
        )
        medallion = MedallionArchitecture(config)
        bronze = list(medallion.bronze_layer.load(
            [{"id": 1, "name": "Alice"}, {"id": 2, "name": None}],
            source="api",
        ))
        silver = medallion.silver_layer.transform(bronze)
        assert len(silver) == 1
        assert silver[0].data["id"] == 1


class TestGoldLayer:
    """Tests for Gold layer operations."""

    def test_aggregate_groups(self) -> None:
        config = MedallionConfig(
            silver_config=SilverToGoldConfig(
                group_by_columns=["category"],
                aggregations={"total": "sum(amount)", "count": "count(amount)"},
            )
        )
        medallion = MedallionArchitecture(config)
        bronze = list(medallion.bronze_layer.load(
            [
                {"id": 1, "category": "A", "amount": 100},
                {"id": 2, "category": "A", "amount": 200},
                {"id": 3, "category": "B", "amount": 50},
            ],
            source="api",
        ))
        silver = medallion.silver_layer.transform(bronze)
        gold = medallion.gold_layer.aggregate(silver)

        assert len(gold) == 2
        for row in gold:
            if row["category"] == "A":
                assert row["total"] == 300
                assert row["count"] == 2
            elif row["category"] == "B":
                assert row["total"] == 50
                assert row["count"] == 1

    def test_aggregate_no_group_by(self) -> None:
        medallion = MedallionArchitecture()
        bronze = list(medallion.bronze_layer.load(
            [{"id": 1, "val": 10}, {"id": 2, "val": 20}],
            source="api",
        ))
        silver = medallion.silver_layer.transform(bronze)
        gold = medallion.gold_layer.aggregate(silver)
        assert len(gold) == 2
        assert gold[0]["val"] == 10


class TestMedallionPipeline:
    """Tests for the end-to-end pipeline."""

    def test_full_pipeline(self) -> None:
        config = MedallionConfig(
            bronze_config=BronzeToSilverConfig(dedup_columns=["id"]),
            silver_config=SilverToGoldConfig(
                group_by_columns=["category"],
                aggregations={"total": "sum(amount)"},
            ),
        )
        pipeline = MedallionPipeline(config)
        records = [
            {"id": 1, "category": "A", "amount": 100},
            {"id": 2, "category": "A", "amount": 200},
            {"id": 1, "category": "A", "amount": 150},  # Duplicate ID
            {"id": 3, "category": "B", "amount": 50},
        ]

        result = pipeline.run(records, source="test")

        # SCD dedup keeps latest by timestamp (no ts, so first seen wins)
        # Actually no timestamp, so first wins per dedup
        assert len(result) > 0

    def test_lineage_recorded(self) -> None:
        pipeline = MedallionPipeline(MedallionConfig())
        bronze = pipeline.medallion.bronze_layer.load(
            [{"id": 1}], source="test"
        )
        silver = pipeline.medallion.silver_layer.transform(bronze)
        gold = pipeline.medallion.gold_layer.aggregate(silver)

        lineage = pipeline.medallion.get_lineage()
        assert len(lineage) == 3
        assert lineage[0]["layer"] == "bronze"
        assert lineage[1]["layer"] == "silver"
        assert lineage[2]["layer"] == "gold"

    def test_lineage_disabled(self) -> None:
        config = MedallionConfig(enable_lineage=False)
        pipeline = MedallionPipeline(config)
        bronze = pipeline.medallion.bronze_layer.load(
            [{"id": 1}], source="test"
        )
        assert len(pipeline.medallion.get_lineage()) == 0
