"""
console_sink.py — Debugging & Console Sink for Streaming
========================================================

PURPOSE:
    Provides local debugging capabilities by printing micro-batch streaming DataFrame contents
    directly to stdout/console. Essential for development, testing, and debugging schema issues.

BUSINESS USE CASE:
    During local development or integration testing, data engineers use console sinks to verify:
    - Proper schema deserialization of JSON/Kafka streams.
    - Watermark progression and window aggregation behavior.
    - Filtering and transformation output before routing data to persistent production sinks.

PRODUCTION WARNING:
    DO NOT use console sink in high-throughput production jobs! Console output blocks worker threads,
    causes driver stdout log bloat, and degrades pipeline throughput.

INTERVIEW QUESTIONS:
    Q: What are the main parameters of format("console") sink in PySpark?
    A: `numRows` (default 20, controls number of rows printed per batch) and `truncate`
       (default True, truncates long string fields).

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Optional
from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class ConsoleStreamSink:
    """
    Console debugging sink for streaming DataFrames.
    """

    @staticmethod
    def print_to_console(
        df: DataFrame,
        query_name: str = "console_debug_query",
        output_mode: str = "append",
        num_rows: int = 20,
        truncate: bool = False,
        trigger_interval: str = "5 seconds",
    ) -> StreamingQuery:
        """
        Write streaming DataFrame output to stdout console.

        Args:
            df: Streaming DataFrame.
            query_name: Stream query identifier name.
            output_mode: "append", "complete", or "update".
            num_rows: Number of rows to display per micro-batch.
            truncate: If True, long column text strings are truncated.
            trigger_interval: Trigger timing interval.

        Returns:
            Active StreamingQuery object.
        """
        logger.info("Starting Console sink stream query '%s' (numRows=%d)", query_name, num_rows)

        writer = (
            df.writeStream
            .format("console")
            .outputMode(output_mode)
            .queryName(query_name)
            .option("numRows", num_rows)
            .option("truncate", str(truncate).lower())
        )

        if trigger_interval.lower() == "once":
            writer = writer.trigger(once=True)
        elif trigger_interval.lower() == "availablenow":
            writer = writer.trigger(availableNow=True)
        else:
            writer = writer.trigger(processingTime=trigger_interval)

        return writer.start()


def debug_stream_to_console(
    df: DataFrame,
    query_name: str = "debug_query",
    num_rows: int = 10,
    output_mode: str = "append",
) -> StreamingQuery:
    """
    Helper function to launch a console debug query quickly.

    Args:
        df: Input streaming DataFrame.
        query_name: Query name.
        num_rows: Max rows printed per micro-batch.
        output_mode: Stream output mode.

    Returns:
        Active StreamingQuery instance.
    """
    return ConsoleStreamSink.print_to_console(
        df,
        query_name=query_name,
        num_rows=num_rows,
        output_mode=output_mode,
        truncate=False,
    )
