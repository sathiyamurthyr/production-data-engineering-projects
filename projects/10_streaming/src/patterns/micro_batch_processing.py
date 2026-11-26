"""
micro_batch_processing.py — Custom foreachBatch Micro-Batch Processing
========================================================================

PURPOSE:
    Provides production patterns using `writeStream.foreachBatch(micro_batch_function)`.
    `foreachBatch` allows applying arbitrary batch DataFrame operations (such as batch joins,
    writes to multiple sinks, third-party API posting, or Delta MERGE upserts) to each micro-batch.

BUSINESS USE CASE:
    1. Multi-Sink Writes: Write each micro-batch simultaneously to Delta Lake (historical storage) AND Redis/DynamoDB (real-time online feature cache).
    2. Delta MERGE Upsert: Update existing dimensional records in Delta Lake while inserting new ones.
    3. Custom Error Handling: Catch and log micro-batch exceptions, routing failing records to a Dead Letter Queue without halting the entire stream.

FOREACHBATCH FUNCTION SIGNATURE:
    ```python
    def process_micro_batch(batch_df: DataFrame, batch_id: int) -> None:
        # batch_df is a STANDARD PySpark BATCH DataFrame!
        # Full batch API (Window functions, collect, write) is fully supported inside this function.
        pass
    ```

INTERVIEW QUESTIONS:
    Q: Why use foreachBatch instead of standard streaming sinks?
    A: Standard sinks (delta, kafka, file) write to a single destination. `foreachBatch` lets you reuse existing batch data writers, write to multiple locations per batch, and run complex Delta `MERGE INTO` logic.

    Q: Is foreachBatch executed on the driver or executors?
    A: The `foreachBatch` outer python function runs on the Spark Driver for every micro-batch; the DataFrame transformations and writes inside it are distributed across Executors.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Callable, List
from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class MicroBatchProcessor:
    """
    Production micro-batch processing patterns using foreachBatch.
    """

    @staticmethod
    def write_to_multiple_sinks(
        batch_df: DataFrame,
        batch_id: int,
        delta_path: str,
        backup_path: str,
    ) -> None:
        """
        Write micro-batch DataFrame to both Delta Lake and Parquet backup simultaneously.

        Args:
            batch_df: Batch DataFrame representing current micro-batch.
            batch_id: Monotonically increasing micro-batch sequence number.
            delta_path: Primary Delta Lake table storage location.
            backup_path: Secondary Parquet backup storage location.
        """
        count = batch_df.count()
        logger.info("Processing micro-batch %d containing %d records", batch_id, count)

        if count == 0:
            logger.debug("Micro-batch %d is empty, skipping writes", batch_id)
            return

        # Write 1: Primary Delta Lake append
        (
            batch_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .save(delta_path)
        )

        # Write 2: Parquet historical archive
        (
            batch_df.write
            .format("parquet")
            .mode("append")
            .save(backup_path)
        )

        logger.info("Successfully committed micro-batch %d to primary and backup sinks", batch_id)

    @staticmethod
    def execute_with_error_handling(
        batch_df: DataFrame,
        batch_id: int,
        primary_write_fn: Callable[[DataFrame, int], None],
        dlq_path: str,
    ) -> None:
        """
        Wrap micro-batch processing in error handling logic to prevent pipeline failure.

        Args:
            batch_df: Batch DataFrame for current micro-batch.
            batch_id: Micro-batch sequence ID.
            primary_write_fn: Custom processing function for valid batch execution.
            dlq_path: Dead Letter Queue storage location for failing micro-batches.
        """
        try:
            primary_write_fn(batch_df, batch_id)
        except Exception as e:
            logger.error("Error processing micro-batch %d: %s. Routing batch to DLQ.", batch_id, str(e))
            (
                batch_df.write
                .format("json")
                .mode("append")
                .save(f"{dlq_path}/batch_{batch_id}")
            )


def start_multi_sink_stream(
    df: DataFrame,
    query_name: str,
    primary_delta_path: str,
    backup_parquet_path: str,
    checkpoint_dir: str = "/tmp/checkpoints",
    trigger_interval: str = "10 seconds",
) -> StreamingQuery:
    """
    Launch a streaming query using foreachBatch for multi-sink persistence.

    Args:
        df: Input streaming DataFrame.
        query_name: Unique query identifier name.
        primary_delta_path: Delta table path.
        backup_parquet_path: Parquet backup path.
        checkpoint_dir: Base checkpoint directory path.
        trigger_interval: Stream trigger interval.

    Returns:
        Active StreamingQuery instance.
    """
    cp = f"{checkpoint_dir}/{query_name}"
    processor = MicroBatchProcessor()

    def handler(batch_df: DataFrame, batch_id: int):
        processor.write_to_multiple_sinks(
            batch_df, batch_id, primary_delta_path, backup_parquet_path
        )

    writer = (
        df.writeStream
        .queryName(query_name)
        .option("checkpointLocation", cp)
        .foreachBatch(handler)
    )

    if trigger_interval.lower() == "availablenow":
        writer = writer.trigger(availableNow=True)
    else:
        writer = writer.trigger(processingTime=trigger_interval)

    return writer.start()
