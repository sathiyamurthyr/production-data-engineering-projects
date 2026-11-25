"""
stream_transformer.py — Stateless Stream Transformations for Structured Streaming
===================================================================================

PURPOSE:
    Provides stateless DataFrame transformations for real-time streaming data.
    Stateless operations (select, filter, withColumn, cast, explode) operate line-by-line
    or row-by-row without keeping track of past micro-batches. Because no state store
    is involved, stateless operations incur minimal memory overhead, zero state store state,
    and achieve maximum micro-batch throughput.

BUSINESS USE CASE:
    In an e-commerce event stream or IoT telemetry pipeline:
    1. Filter out malformed, test, or invalid events immediately at ingestion.
    2. Extract nested attributes from JSON properties.
    3. Normalize timestamps and standardize currency values.
    4. Categorize risk level or user tier dynamically using conditional logic.

PRODUCTION EXAMPLE:
    from src.transformations.stream_transformer import StreamTransformer

    transformer = StreamTransformer()
    cleaned_df = (
        df
        .pipe(transformer.filter_valid_events)
        .pipe(transformer.extract_nested_properties)
        .pipe(transformer.normalize_event_timestamps)
        .pipe(transformer.add_ingestion_metadata)
    )

PERFORMANCE NOTES:
    - Stateless operations do NOT require shuffle or watermark.
    - Spark maps these transformations directly into JVM byte code via Catalyst CodeGen.
    - Always place stateless filters as early in the pipeline as possible (Filter Pushdown)
      to minimize payload size prior to stateful operations or sinks.

INTERVIEW QUESTIONS:
    Q: What is the difference between stateless and stateful operations in Structured Streaming?
    A: Stateless operations (filter, select, map) process each row independently without
       memory of previous rows or micro-batches. Stateful operations (groupBy, window,
       dropDuplicates, joins) maintain state across micro-batches using an in-memory or
       RocksDB StateStore.

    Q: Can stateless operations break streaming output modes?
    A: No. Stateless operations work seamlessly with all three output modes: Append, Update,
       and Complete.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, TimestampType

logger = logging.getLogger(__name__)


class StreamTransformer:
    """
    Production transformation utility for stateless streaming DataFrame operations.
    """

    @staticmethod
    def filter_valid_events(
        df: DataFrame,
        id_column: str = "event_id",
        required_cols: Optional[List[str]] = None,
    ) -> DataFrame:
        """
        Filter out records with missing event IDs or null essential fields.

        Args:
            df: Streaming DataFrame.
            id_column: Unique event identifier column.
            required_cols: Additional columns that must not be null.

        Returns:
            Filtered streaming DataFrame.
        """
        condition = F.col(id_column).isNotNull() & (F.col(id_column) != "")
        
        if required_cols:
            for col in required_cols:
                if col in df.columns:
                    condition = condition & F.col(col).isNotNull()

        logger.info("Applying stateless event filtering on column: %s", id_column)
        return df.filter(condition)

    @staticmethod
    def extract_nested_properties(
        df: DataFrame,
        properties_col: str = "properties",
    ) -> DataFrame:
        """
        Extract key attributes from raw JSON text or string payload into top-level columns.

        Args:
            df: Streaming DataFrame.
            properties_col: Column containing raw JSON key-value string.

        Returns:
            DataFrame with enriched extracted top-level columns.
        """
        if properties_col not in df.columns:
            logger.warning("Column %s not present in DataFrame, returning unmodified.", properties_col)
            return df

        return (
            df
            .withColumn("referrer", F.get_json_object(F.col(properties_col), "$.referrer"))
            .withColumn("campaign_id", F.get_json_object(F.col(properties_col), "$.campaign_id"))
            .withColumn("session_duration", F.get_json_object(F.col(properties_col), "$.session_duration").cast(DoubleType()))
        )

    @staticmethod
    def normalize_event_timestamps(
        df: DataFrame,
        ts_col: str = "event_timestamp",
        output_ts_col: str = "event_time",
    ) -> DataFrame:
        """
        Convert String ISO-8601 timestamps to PySpark TimestampType.

        Args:
            df: Streaming DataFrame.
            ts_col: Source timestamp column name.
            output_ts_col: Destination TimestampType column name.

        Returns:
            DataFrame with typed timestamp column.
        """
        if ts_col not in df.columns:
            return df

        # If already timestamp, alias or retain
        if isinstance(df.schema[ts_col].dataType, TimestampType):
            return df.withColumn(output_ts_col, F.col(ts_col))

        return df.withColumn(
            output_ts_col,
            F.coalesce(
                F.to_timestamp(F.col(ts_col), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"),
                F.to_timestamp(F.col(ts_col), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"),
                F.to_timestamp(F.col(ts_col), "yyyy-MM-dd'T'HH:mm:ss"),
                F.to_timestamp(F.col(ts_col), "yyyy-MM-dd HH:mm:ss")
            )
        )

    @staticmethod
    def add_ingestion_metadata(df: DataFrame) -> DataFrame:
        """
        Add processing timestamp and environment lineage columns to each micro-batch record.

        Args:
            df: Streaming DataFrame.

        Returns:
            DataFrame with ingestion metadata columns added.
        """
        return (
            df
            .withColumn("processed_at", F.current_timestamp())
            .withColumn("processing_date", F.current_date())
        )

    @staticmethod
    def categorize_event_severity(
        df: DataFrame,
        amount_col: str = "price",
        severity_col: str = "event_tier",
    ) -> DataFrame:
        """
        Categorize records based on dynamic business logic thresholds.

        Args:
            df: Streaming DataFrame.
            amount_col: Numeric column used for tiering.
            severity_col: Output tier label column name.

        Returns:
            DataFrame with tiering column applied.
        """
        if amount_col not in df.columns:
            return df.withColumn(severity_col, F.lit("STANDARD"))

        return df.withColumn(
            severity_col,
            F.when(F.col(amount_col) >= 500.0, F.lit("HIGH_VALUE"))
             .when(F.col(amount_col) >= 100.0, F.lit("MEDIUM_VALUE"))
             .otherwise(F.lit("STANDARD"))
        )


def apply_stateless_transformations(df: DataFrame) -> DataFrame:
    """
    Standard pipeline helper executing all default stateless transformations sequentially.

    Args:
        df: Raw streaming DataFrame from source.

    Returns:
        Cleaned, normalized streaming DataFrame.
    """
    transformer = StreamTransformer()
    return (
        df
        .transform(lambda d: transformer.filter_valid_events(d, id_column="event_id"))
        .transform(lambda d: transformer.normalize_event_timestamps(d, ts_col="event_timestamp"))
        .transform(lambda d: transformer.extract_nested_properties(d))
        .transform(lambda d: transformer.categorize_event_severity(d))
        .transform(lambda d: transformer.add_ingestion_metadata(d))
    )
