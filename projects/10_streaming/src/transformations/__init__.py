"""
Transformations subpackage for streaming data engineering.
"""
from src.transformations.stream_transformer import StreamTransformer, apply_stateless_transformations
from src.transformations.windowed_aggregations import WindowedAggregator, aggregate_stream_metrics
from src.transformations.stream_joins import StreamJoiner, enrich_events_with_lookup
from src.transformations.deduplication import StreamDeduplicator, deduplicate_stream

__all__ = [
    "StreamTransformer",
    "apply_stateless_transformations",
    "WindowedAggregator",
    "aggregate_stream_metrics",
    "StreamJoiner",
    "enrich_events_with_lookup",
    "StreamDeduplicator",
    "deduplicate_stream",
]
