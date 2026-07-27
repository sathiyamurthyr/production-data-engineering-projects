"""
Enterprise Spark Structured Streaming

Production patterns for real-time pipelines.
"""

from typing import Any


def create_streaming_query(
    spark: Any,
    source_format: str = "kafka",
    source_options: dict[str, Any] | None = None,
) -> Any:
    """
    Create production streaming query.
    
    Business Use Case: Real-time event processing.
    """
    reader = spark.readStream.format(source_format)

    if source_options:
        for key, value in source_options.items():
            reader = reader.option(key, value)

    return reader.load()


def streaming_with_watermark(
    df: Any,
    timestamp_col: str = "event_time",
    watermark_delay: str = "30 minutes",
) -> Any:
    """
    Apply watermark for late data handling.
    
    Business Use Case: Processing out-of-order events.
    """
    return df.withWatermark(timestamp_col, watermark_delay)


def tumbling_window(
    df: Any,
    window_col: str,
    window_duration: str = "5 minutes",
) -> Any:
    """
    Apply tumbling window aggregation.
    
    Business Use Case: Time-based aggregations.
    """
    from pyspark.sql.functions import window, col

    return df.groupBy(window(col(window_col), window_duration)).count()


def exactly_once_write(
    df: Any,
    checkpoint_path: str,
    output_mode: str = "append",
) -> Any:
    """
    Write with exactly-once guarantees.
    
    Business Use Case: Reliable stream output.
    """
    return (
        df.writeStream.format("delta")
        .outputMode(output_mode)
        .option("checkpointLocation", checkpoint_path)
        .trigger(processingTime="1 minute")
    )