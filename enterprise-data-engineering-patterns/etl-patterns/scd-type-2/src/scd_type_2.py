"""SCD Type 2 pattern - Production implementation.

Implements Slowly Changing Dimension Type 2 with versioned records,
surrogate keys, and effective dating. Supports both batch and
incremental merge scenarios with data quality validation.

Typical use cases:
    - Dimension table management in data warehouses
    - Customer/employee slowly changing attributes
    - Product catalog versioning
    - Type 2 SCD in Delta Lake / Snowflake

References:
    - Kimball Group SCD Type 2: https://www.kimballgroup.com/data-warehouse-business-intelligence/dimensional-modeling/
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SCD2Config(BaseModel):
    """Configuration for SCD Type 2 pattern."""

    pattern_name: str = Field(default="scd-type-2")
    business_key_columns: list[str] = Field(
        default_factory=list,
        description="Columns that uniquely identify a business entity",
    )
    tracked_columns: list[str] = Field(
        default_factory=list,
        description="Columns whose changes trigger new versions",
    )
    effective_date_column: str = Field(
        default="effective_from",
        description="Column name for effective start date",
    )
    expiry_date_column: str = Field(
        default="effective_to",
        description="Column name for effective end date",
    )
    is_current_column: str = Field(
        default="is_current",
        description="Column name for current flag",
    )
    surrogate_key_column: str = Field(
        default="surrogate_key",
        description="Column name for surrogate key",
    )
    default_expiry: str = Field(
        default="9999-12-31",
        description="Default expiry date for current records",
    )


class SCD2Record(BaseModel):
    """A Type 2 SCD record with versioning metadata."""

    business_key: str
    data: dict[str, Any]
    surrogate_key: int
    effective_from: datetime
    effective_to: str = "9999-12-31 23:59:59"
    is_current: bool = True
    version: int = 1
    source_timestamp: datetime | None = None

    def compute_surrogate_key(self) -> int:
        """Compute surrogate key from business key and effective date."""
        key_str = f"{self.business_key}_{self.effective_from.isoformat()}"
        return abs(hash(key_str)) % (2**31)

    def close_record(self) -> None:
        """Close this record (set as not current)."""
        self.is_current = False
        self.effective_to = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class SCD2TypeTwo:
    """SCD Type 2 implementation with full versioning.

    This pattern manages slowly changing dimensions by:
    - Generating surrogate keys for each record version
    - Tracking effective date ranges (effective_from, effective_to)
    - Maintaining an is_current flag for active versions
    - Version numbering for audit trail

    Args:
        config: SCD Type 2 configuration.

    Example:
        >>> config = SCD2Config(business_key_columns=["customer_id"])
        >>> scd = SCD2TypeTwo(config)
        >>> changes = scd.detect_changes(existing, incoming)
        >>> updates = scd.apply_changes(changes)
    """

    def __init__(self, config: SCD2Config | None = None) -> None:
        self.config = config or SCD2Config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def compute_business_key(self, record: dict[str, Any]) -> str:
        """Extract and compute the business key from a record.

        Args:
            record: Source data record.

        Returns:
            Computed business key string.
        """
        key_parts = []
        for col in self.config.business_key_columns:
            val = record.get(col, "")
            key_parts.append(str(val))
        return "|".join(key_parts) if key_parts else str(record)

    def compute_data_hash(self, record: dict[str, Any]) -> str:
        """Compute a hash of the tracked columns for change detection.

        Args:
            record: Source data record.

        Returns:
            MD5 hash of the tracked column values.
        """
        tracked = {}
        if self.config.tracked_columns:
            for col in self.config.tracked_columns:
                tracked[col] = record.get(col)
        else:
            tracked = dict(record)

        hash_input = str(sorted(tracked.items()))
        return hashlib.md5(hash_input.encode()).hexdigest()

    def detect_changes(
        self,
        existing_records: list[dict[str, Any]],
        incoming_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect changes between existing and incoming records.

        Args:
            existing_records: Current records in the dimension table.
            incoming_records: New records from source.

        Returns:
            List of change records with actions (INSERT/UPDATE).
        """
        # Index existing records by business key
        existing_by_key: dict[str, list[dict[str, Any]]] = {}
        for rec in existing_records:
            biz_key = self.compute_business_key(rec)
            existing_by_key.setdefault(biz_key, []).append(rec)

        changes: list[dict[str, Any]] = []

        for incoming in incoming_records:
            biz_key = self.compute_business_key(incoming)
            incoming_hash = self.compute_data_hash(incoming)

            if biz_key not in existing_by_key:
                # New entity - INSERT
                changes.append({
                    "action": "INSERT",
                    "business_key": biz_key,
                    "data": incoming,
                    "data_hash": incoming_hash,
                })
            else:
                # Check current version for changes
                current_recs = [
                    r for r in existing_by_key[biz_key]
                    if r.get(self.config.is_current_column, True)
                ]

                for current in current_recs:
                    existing_hash = self.compute_data_hash(current)

                    if existing_hash != incoming_hash:
                        # Changed - UPDATE (close old, insert new)
                        changes.append({
                            "action": "UPDATE",
                            "business_key": biz_key,
                            "old_record": current,
                            "new_data": incoming,
                            "data_hash": incoming_hash,
                        })
                    else:
                        # No change - skip
                        changes.append({
                            "action": "NO_CHANGE",
                            "business_key": biz_key,
                            "data": incoming,
                            "data_hash": incoming_hash,
                        })

        self.logger.info(
            "Change detection complete",
            total_changes=len(changes),
            inserts=sum(1 for c in changes if c["action"] == "INSERT"),
            updates=sum(1 for c in changes if c["action"] == "UPDATE"),
            no_changes=sum(1 for c in changes if c["action"] == "NO_CHANGE"),
        )

        return changes

    def apply_changes(
        self,
        changes: list[dict[str, Any]],
        existing_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply detected changes to produce the new dimension table.

        Args:
            changes: Change records from detect_changes().
            existing_records: Current dimension records.

        Returns:
            Updated list of dimension records with versioning.
        """
        # Start with existing records
        result = [dict(r) for r in existing_records]

        # Build index of existing records by business key
        existing_by_key: dict[str, list[dict[str, Any]]] = {}
        for rec in result:
            biz_key = self.compute_business_key(rec)
            existing_by_key.setdefault(biz_key, []).append(rec)

        for change in changes:
            if change["action"] == "INSERT":
                # Create new current record
                new_rec = self._create_new_record(
                    change["business_key"],
                    change["data"],
                    version=1,
                )
                result.append(new_rec)

            elif change["action"] == "UPDATE":
                # Close the old current record
                old_recs = existing_by_key.get(change["business_key"], [])
                max_version = max(
                    (r.get("version", 0) for r in old_recs if r.get(
                        self.config.is_current_column, True
                    )),
                    default=0,
                )

                for rec in result:
                    if (self.compute_business_key(rec) == change["business_key"]
                            and rec.get(self.config.is_current_column, True)):
                        rec[self.config.is_current_column] = False
                        rec[self.config.expiry_date_column] = (
                            datetime.now(timezone.utc)
                                .strftime("%Y-%m-%d %H:%M:%S")
                        )

                # Insert new current record
                new_rec = self._create_new_record(
                    change["business_key"],
                    change["new_data"],
                    version=max_version + 1,
                )
                result.append(new_rec)

        self.logger.info(
            "SCD Type 2 changes applied",
            total_records=len(result),
            inserts=sum(1 for c in changes if c["action"] == "INSERT"),
            updates=sum(1 for c in changes if c["action"] == "UPDATE"),
        )

        return result

    def _create_new_record(
        self,
        business_key: str,
        data: dict[str, Any],
        version: int,
    ) -> dict[str, Any]:
        """Create a new current record with versioning metadata.

        Args:
            business_key: The business key value.
            data: The record data.
            version: The version number.

        Returns:
            New record dictionary with SCD2 metadata.
        """
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        record = dict(data)
        record[self.config.effective_date_column] = now_str
        record[self.config.expiry_date_column] = self.config.default_expiry
        record[self.config.is_current_column] = True
        record["version"] = version
        record["business_key"] = business_key
        record[self.config.surrogate_key_column] = hash(business_key) % (2**31)

        return record

    def get_current_records(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter to only current (active) records.

        Args:
            records: All versioned records.

        Returns:
            Only records with is_current=True.
        """
        return [
            r for r in records
            if r.get(self.config.is_current_column, True)
        ]

    def get_history_for_key(
        self, records: list[dict[str, Any]], business_key: str
    ) -> list[dict[str, Any]]:
        """Get all historical versions for a specific business key.

        Args:
            records: All versioned records.
            business_key: The business key to look up.

        Returns:
            All version records for the key, sorted by version.
        """
        history = [
            r for r in records
            if self.compute_business_key(r) == business_key
        ]
        return sorted(history, key=lambda r: r.get("version", 0))


class SCD2Pipeline:
    """End-to-end SCD Type 2 pipeline.

    Args:
        config: SCD Type 2 configuration.

    Example:
        >>> pipeline = SCD2Pipeline(SCD2Config(business_key_columns=["customer_id"]))
        >>> updated = pipeline.run(existing, incoming)
    """

    def __init__(self, config: SCD2Config | None = None) -> None:
        self.config = config or SCD2Config()
        self.scd = SCD2TypeTwo(self.config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(
        self,
        existing_records: list[dict[str, Any]],
        incoming_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run the full SCD Type 2 pipeline.

        Args:
            existing_records: Current dimension table records.
            incoming_records: New source records.

        Returns:
            Updated dimension table with versioned records.
        """
        self.logger.info(
            "Starting SCD Type 2 pipeline",
            existing_count=len(existing_records),
            incoming_count=len(incoming_records),
        )

        changes = self.scd.detect_changes(existing_records, incoming_records)
        updated = self.scd.apply_changes(changes, existing_records)

        current = self.scd.get_current_records(updated)
        self.logger.info(
            "SCD Type 2 pipeline completed",
            total_records=len(updated),
            current_records=len(current),
        )

        return updated
