"""Medallion Architecture pattern - Production implementation.

This module implements the Medallion Architecture (Bronze/Silver/Gold)
with full data quality, lineage tracking, and idempotent processing.

Typical use cases:
    - Lakehouse data ingestion pipelines
    - Bronze-to-Gold ETL workflows
    - Incremental data processing with CDC
    - Cross-domain data sharing with quality guarantees

References:
    - Delta Lake Medallion Architecture: https://learn.microsoft.com/azure/databricks/delta/delta-live-tables
    - Lakehouse Pattern: https://databricks.com/glossary/medallion-architecture
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Layer(str, Enum):
    """Medallion architecture layer."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class BronzeToSilverConfig(BaseModel):
    """Configuration for Bronze-to-Silver transformation."""

    dedup_columns: list[str] = Field(
        default_factory=list,
        description="Columns to deduplicate on (keeps latest by timestamp)",
    )
    timestamp_column: str = Field(
        default="_loaded_at",
        description="Timestamp column for deduplication ordering",
    )
    drop_columns: list[str] = Field(
        default_factory=list,
        description="Columns to drop during cleaning",
    )
    quality_checks: list[str] = Field(
        default_factory=lambda: ["not_null", "no_duplicates"],
        description="Quality checks to apply",
    )


class SilverToGoldConfig(BaseModel):
    """Configuration for Silver-to-Gold aggregation."""

    group_by_columns: list[str] = Field(
        default_factory=list,
        description="Columns to group by for aggregation",
    )
    aggregations: dict[str, str] = Field(
        default_factory=dict,
        description="Aggregation definitions {output_col: agg_expr}",
    )
    window_columns: list[str] = Field(
        default_factory=list,
        description="Columns for windowed aggregation",
    )


class MedallionConfig(BaseModel):
    """Configuration for the Medallion Architecture pattern."""

    pattern_name: str = Field(default="medallion-architecture")
    bronze_config: BronzeToSilverConfig = Field(default_factory=BronzeToSilverConfig)
    silver_config: SilverToGoldConfig = Field(default_factory=SilverToGoldConfig)
    enable_lineage: bool = Field(default=True)
    enable_quality_checks: bool = Field(default=True)
    checkpoint_path: str | None = Field(default=None)


class DataRecord(BaseModel):
    """A single data record with metadata."""

    data: dict[str, Any] = Field(default_factory=dict)
    source_table: str = Field(default="")
    partition: str = Field(default="")
    checksum: str = Field(default="")
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def compute_checksum(self) -> str:
        """Compute a checksum for this record's data."""
        data_str = str(sorted(self.data.items()))
        return hashlib.md5(data_str.encode()).hexdigest()


class MedallionArchitecture:
    """Medallion Architecture (Bronze/Silver/Gold) implementation.

    This pattern provides a layered data architecture:
    - **Bronze**: Raw, unprocessed data ingested as-is
    - **Silver**: Cleaned, deduplicated, and conformed data
    - **Gold**: Aggregated, business-ready data

    Args:
        config: Pattern configuration.

    Example:
        >>> config = MedallionConfig()
        >>> pattern = MedallionArchitecture(config)
        >>> bronze = pattern.bronze_layer.load(raw_data, source="api")
        >>> silver = pattern.silver_layer.transform(bronze)
        >>> gold = pattern.gold_layer.aggregate(silver)
    """

    def __init__(self, config: MedallionConfig | None = None) -> None:
        self.config = config or MedallionConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._lineage: list[dict[str, Any]] = []

    @property
    def bronze_layer(self) -> _BronzeLayer:
        """Access the Bronze layer."""
        return _BronzeLayer(self)

    @property
    def silver_layer(self) -> _SilverLayer:
        """Access the Silver layer."""
        return _SilverLayer(self)

    @property
    def gold_layer(self) -> _GoldLayer:
        """Access the Gold layer."""
        return _GoldLayer(self)

    def _record_lineage(
        self,
        layer: Layer,
        source: str,
        record_count: int,
        checksum: str,
    ) -> None:
        """Record lineage information for a transformation step."""
        if not self.config.enable_lineage:
            return
        entry = {
            "layer": layer.value,
            "source": source,
            "record_count": record_count,
            "checksum": checksum,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._lineage.append(entry)
        self.logger.info("Lineage recorded", **entry)

    def get_lineage(self) -> list[dict[str, Any]]:
        """Return the accumulated lineage records."""
        return self._lineage.copy()


class _BronzeLayer:
    """Bronze layer: raw, immutable, unprocessed data."""

    def __init__(self, parent: MedallionArchitecture) -> None:
        self._parent = parent
        self.logger = logging.getLogger(f"{__name__}._BronzeLayer")

    def load(
        self,
        records: list[dict[str, Any]],
        source: str = "unknown",
        partition: str = "",
    ) -> list[DataRecord]:
        """Load raw records into the Bronze layer.

        Args:
            records: Raw data records as dictionaries.
            source: Source system identifier.
            partition: Partition value (e.g., date string).

        Returns:
            List of DataRecord objects with metadata.
        """
        self.logger.info(
            "Loading records to Bronze layer",
            source=source,
            record_count=len(records),
            partition=partition,
        )

        result: list[DataRecord] = []
        for record in records:
            dr = DataRecord(
                data=record,
                source_table=source,
                partition=partition or "default",
                loaded_at=datetime.now(timezone.utc),
            )
            dr.checksum = dr.compute_checksum()
            result.append(dr)

        self._parent._record_lineage(
            Layer.BRONZE, source, len(result),
            hashlib.md5(str(len(result)).encode()).hexdigest(),
        )
        return result


class _SilverLayer:
    """Silver layer: cleaned, deduplicated, conformed data."""

    def __init__(self, parent: MedallionArchitecture) -> None:
        self._parent = parent
        self.logger = logging.getLogger(f"{__name__}._SilverLayer")

    def transform(
        self,
        bronze_records: list[DataRecord],
    ) -> list[DataRecord]:
        """Transform Bronze records into Silver (cleaned, deduplicated).

        Args:
            bronze_records: Records from the Bronze layer.

        Returns:
            Cleaned and deduplicated records.
        """
        cfg = self._parent.config.bronze_config
        self.logger.info(
            "Transforming Bronze to Silver",
            record_count=len(bronze_records),
            dedup_columns=cfg.dedup_columns,
            quality_checks=cfg.quality_checks,
        )

        # Drop specified columns
        for dr in bronze_records:
            for col in cfg.drop_columns:
                dr.data.pop(col, None)

        # Deduplicate
        if cfg.dedup_columns:
            seen: dict[tuple, DataRecord] = {}
            ts_col = cfg.timestamp_column
            for dr in bronze_records:
                key = tuple(dr.data.get(col) for col in cfg.dedup_columns)
                if key in seen:
                    existing = seen[key]
                    existing_ts = existing.data.get(ts_col, "")
                    new_ts = dr.data.get(ts_col, "")
                    if new_ts > existing_ts:
                        seen[key] = dr
                else:
                    seen[key] = dr
            result = list(seen.values())
        else:
            # Use checksum-based deduplication
            seen_checksums: set[str] = set()
            result = []
            for dr in bronze_records:
                if dr.checksum not in seen_checksums:
                    seen_checksums.add(dr.checksum)
                    result.append(dr)

        # Apply quality checks
        if self._parent.config.enable_quality_checks:
            result = self._apply_quality_checks(result, cfg.quality_checks)

        self._parent._record_lineage(
            Layer.SILVER, "bronze_transform", len(result),
            hashlib.md5(str(len(result)).encode()).hexdigest(),
        )
        return result

    def _apply_quality_checks(
        self,
        records: list[DataRecord],
        checks: list[str],
    ) -> list[DataRecord]:
        """Apply data quality checks to records."""
        result = records
        for check in checks:
            if check == "not_null":
                result = [
                    r for r in result
                    if all(v is not None for v in r.data.values())
                ]
            elif check == "no_duplicates":
                seen: set[str] = set()
                deduped: list[DataRecord] = []
                for r in result:
                    if r.checksum not in seen:
                        seen.add(r.checksum)
                        deduped.append(r)
                result = deduped
            elif check == "no_empty_strings":
                result = [
                    r for r in result
                    if all(
                        v != "" if v is not None else True
                        for v in r.data.values()
                    )
                ]
        return result


class _GoldLayer:
    """Gold layer: aggregated, business-ready data."""

    def __init__(self, parent: MedallionArchitecture) -> None:
        self._parent = parent
        self.logger = logging.getLogger(f"{__name__}._GoldLayer")

    def aggregate(
        self,
        silver_records: list[DataRecord],
    ) -> list[dict[str, Any]]:
        """Aggregate Silver records into Gold-layer business entities.

        Args:
            silver_records: Records from the Silver layer.

        Returns:
            List of aggregated dictionaries ready for consumption.
        """
        cfg = self._parent.config.silver_config
        self.logger.info(
            "Aggregating Silver to Gold",
            record_count=len(silver_records),
            group_by=cfg.group_by_columns,
        )

        if not cfg.group_by_columns:
            # No aggregation, just flatten
            return [dr.data for dr in silver_records]

        # Group and aggregate
        groups: dict[tuple, list[dict[str, Any]]] = {}
        for dr in silver_records:
            key = tuple(dr.data.get(col) for col in cfg.group_by_columns)
            groups.setdefault(key, []).append(dr.data)

        result: list[dict[str, Any]] = []
        for key, records in groups.items():
            agg_record: dict[str, Any] = {}
            # Add group-by columns
            for i, col in enumerate(cfg.group_by_columns):
                agg_record[col] = key[i]

            # Apply aggregations
            for out_col, agg_expr in cfg.aggregations.items():
                agg_record[out_col] = self._apply_aggregation(
                    records, agg_expr
                )

            result.append(agg_record)

        self._parent._record_lineage(
            Layer.GOLD, "silver_aggregate", len(result),
            hashlib.md5(str(len(result)).encode()).hexdigest(),
        )
        return result

    def _apply_aggregation(
        self,
        records: list[dict[str, Any]],
        agg_expr: str,
    ) -> Any:
        """Apply an aggregation expression to records.

        Supports: count, sum, avg, min, max, first, last
        """
        parts = agg_expr.split("(", 1)
        if len(parts) != 2:
            return None
        func = parts[0].strip().lower()
        col = parts[1].rstrip(")").strip()
        values = [r.get(col) for r in records if r.get(col) is not None]

        if not values:
            return None

        if func == "count":
            return len(values)
        elif func == "sum":
            return sum(values)
        elif func == "avg":
            return sum(values) / len(values)
        elif func == "min":
            return min(values)
        elif func == "max":
            return max(values)
        elif func == "first":
            return values[0]
        elif func == "last":
            return values[-1]
        return None


class MedallionPipeline:
    """End-to-end Medallion pipeline orchestrator.

    Args:
        config: Pipeline configuration.

    Example:
        >>> pipeline = MedallionPipeline(MedallionConfig())
        >>> result = pipeline.run(raw_records, source="orders_api")
    """

    def __init__(self, config: MedallionConfig | None = None) -> None:
        self.config = config or MedallionConfig()
        self.medallion = MedallionArchitecture(self.config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(
        self,
        raw_records: list[dict[str, Any]],
        source: str = "unknown",
        partition: str = "",
    ) -> list[dict[str, Any]]:
        """Execute the full Bronze -> Silver -> Gold pipeline.

        Args:
            raw_records: Raw input data records.
            source: Source system identifier.
            partition: Partition value.

        Returns:
            Gold-layer aggregated results.
        """
        self.logger.info(
            "Starting Medallion pipeline",
            source=source,
            input_count=len(raw_records),
        )

        # Bronze: load raw
        bronze = self.medallion.bronze_layer.load(
            raw_records, source=source, partition=partition
        )

        # Silver: clean and deduplicate
        silver = self.medallion.silver_layer.transform(bronze)

        # Gold: aggregate
        gold = self.medallion.gold_layer.aggregate(silver)

        self.logger.info(
            "Medallion pipeline completed",
            bronze_count=len(bronze),
            silver_count=len(silver),
            gold_count=len(gold),
            lineage_count=len(self.medallion.get_lineage()),
        )

        return gold
