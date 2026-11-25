"""
file_sink.py — Streaming File Sink (Parquet, JSON, CSV)
======================================================

PURPOSE:
    Implements streaming file destination output sinks (Parquet, JSON, CSV) using Structured Streaming.
    File sinks support `append` output mode and require explicit checkpoint directories to guarantee
    fault tolerance and exactly-once execution.

BUSINESS USE CASE:
    - Archival Layer: Continuously archive raw streaming events in compressed Parquet format to long-term cloud storage (S3 Glacier / ADLS Cool tier).
    - Inter-system File Delivery: Export processed micro-batch metrics into CSV files for downstream legacy systems.

PRODUCTION SINK RULES:
    - File sinks ONLY support `append` output mode (cannot overwrite or update individual files in place without Delta Lake).
    - Partitioning: Partition output files by time fields (e.g. `processing_date=2026-07-20/hour=14/`) to prevent single-directory file listing overhead.
    - Checkpoint: Mandatory. Without checkpointing, Spark refuses to start file writeStream.

INTERVIEW QUESTIONS:
    Q: Why does standard file stream sink only support `append` output mode?
    A: Standard file formats (Parquet, CSV, JSON) are immutable. Standard Spark file sinks cannot update existing files on disk mid-stream. To perform inplace updates or deletes in real-time streaming, you must use Delta Lake.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class FileStreamSink:
    """
    Production file streaming sink for standard storage formats (Parquet, JSON, CSV).
    """

    def __init__(self, checkpoint_base_path: str = "/tmp/file_sink_checkpoints") -> None:
        """
        Initialise file streaming sink.

        Args:
            checkpoint_base_path: Base path for stream checkpoints.
        """
        self.checkpoint_base_path = checkpoint_base_path

    def write_to_file(
        self,
        df: DataFrame,
        output_path: str,
        query_name: str,
        file_format: str = "parquet",
        partition_cols: Optional[List[str]] = None,
        trigger_interval: str = "1 minute",
        checkpoint_path: Optional[str] = None,
    ) -> StreamingQuery:
        """
        Write streaming DataFrame to file-based target directory.

        Args:
            df: Input streaming DataFrame.
            output_path: Destination file directory path.
            query_name: Streaming query identifier name.
            file_format: Output file format ("parquet", "json", "csv").
            partition_cols: Directory partitioning column list.
            trigger_interval: Trigger timing interval.
            checkpoint_path: Storage path for streaming query checkpoint.

        Returns:
            Active StreamingQuery object.
        """
        cp = checkpoint_path or f"{self.checkpoint_base_path}/{query_name}"
        logger.info(
            "Starting File stream query '%s': format=%s, path=%s, checkpoint=%s",
            query_name,
            file_format,
            output_path,
            cp,
        )

        writer = (
            df.writeStream
            .format(file_format)
            .outputMode("append")  # Standard file sinks only support append mode
            .queryName(query_name)
            .option("checkpointLocation", cp)
        )

        if file_format.lower() == "csv":
            writer = writer.option("header", "true")

        if partition_cols:
            writer = writer.partitionBy(*partition_cols)

        if trigger_interval.lower() == "availablenow":
            writer = writer.trigger(availableNow=True)
        else:
            writer = writer.trigger(processingTime=trigger_interval)

        return writer.start(output_path)


def stream_to_parquet(
    df: DataFrame,
    output_path: str,
    query_name: str,
    checkpoint_dir: str = "/tmp/checkpoints",
    partition_cols: Optional[List[str]] = None,
) -> StreamingQuery:
    """
    Convenience function for streaming DataFrame to Parquet files.

    Args:
        df: Input streaming DataFrame.
        output_path: Target directory path.
        query_name: Streaming query identifier.
        checkpoint_dir: Checkpoint directory path.
        partition_cols: Partition columns list.

    Returns:
        Active StreamingQuery instance.
    """
    sink = FileStreamSink(checkpoint_base_path=checkpoint_dir)
    return sink.write_to_file(
        df,
        output_path=output_path,
        query_name=query_name,
        file_format="parquet",
        partition_cols=partition_cols,
    )
