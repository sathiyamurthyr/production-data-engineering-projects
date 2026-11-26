"""
Sinks subpackage for streaming output destinations.
"""
from src.sinks.delta_sink import DeltaStreamSink, write_to_delta_table
from src.sinks.kafka_sink import KafkaStreamSink, write_to_kafka_topic
from src.sinks.console_sink import ConsoleStreamSink, debug_stream_to_console
from src.sinks.file_sink import FileStreamSink, stream_to_parquet

__all__ = [
    "DeltaStreamSink",
    "write_to_delta_table",
    "KafkaStreamSink",
    "write_to_kafka_topic",
    "ConsoleStreamSink",
    "debug_stream_to_console",
    "FileStreamSink",
    "stream_to_parquet",
]
