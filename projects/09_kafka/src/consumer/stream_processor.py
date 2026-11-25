"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/consumer/stream_processor.py

Stream Processing Pipeline Module.

Implements real-time stream processing patterns:
- Stateless transformation (map, filter, enrich)
- Stateful windowed aggregation (tumbling & sliding windows)
- Alert condition evaluation (threshold breach detection)
- DLQ routing on processing failure

Business Use Case:
  Real-time feature processing & anomaly detection. Calculates aggregate metrics
  over time windows (e.g. 5-minute total sales per region, average sensor temperature)
  and routes high-value triggers to alerting subsystems.

Production Example:
  IoT telemetry stream processor consumes 100K readings/sec. Aggregates average vibration
  over a 1-minute tumbling window. If avg vibration > 8.5 mm/s, emits an urgent alert.

Interview Questions:
  Q: What is the difference between a tumbling window and a sliding window?
  A: Tumbling window: Fixed-size, non-overlapping time intervals (e.g. 00:00-00:05, 00:05-00:10).
     Sliding window: Fixed-size, overlapping intervals defined by window size and slide interval
     (e.g. 5-minute window sliding every 1 minute).

  Q: How do you handle late-arriving data in real-time stream processing?
  A: 1. Event time vs Processing time watermarking
     2. Allowed lateness thresholds (drop or write to late-data DLQ topic)
     3. Update/upsert window state when late events arrive within allowed bound
"""

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.consumer.kafka_consumer import ProcessedMessage

logger = logging.getLogger(__name__)


@dataclass
class WindowResult:
    """Aggregated window result payload."""
    window_start: datetime
    window_end: datetime
    group_key: str
    metric_name: str
    count: int
    sum_val: float
    avg_val: float
    min_val: float
    max_val: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "group_key": self.group_key,
            "metric_name": self.metric_name,
            "count": self.count,
            "sum_val": round(self.sum_val, 4),
            "avg_val": round(self.avg_val, 4),
            "min_val": round(self.min_val, 4),
            "max_val": round(self.max_val, 4),
        }


class TumblingWindowAggregator:
    """
    In-Memory Tumbling Window Aggregator for event streams.

    Group key + fixed time window buckets (e.g., 60 seconds).
    """

    def __init__(self, window_size_sec: int = 60, key_extractor: Optional[Callable[[Dict[str, Any]], str]] = None):
        self.window_size_sec = window_size_sec
        self.key_extractor = key_extractor or (lambda val: val.get("region", "global"))
        # Window key: (window_start_epoch, group_key) -> List[float]
        self._windows: Dict[Tuple[int, str], List[float]] = {}

    def _get_window_start_epoch(self, dt: datetime) -> int:
        timestamp_sec = int(dt.timestamp())
        return timestamp_sec - (timestamp_sec % self.window_size_sec)

    def add_event(self, msg: ProcessedMessage, value_extractor: Callable[[Dict[str, Any]], float]) -> None:
        """Add an event to the corresponding window bucket."""
        val = msg.value
        payload = val.get("payload", val)
        group_key = self.key_extractor(payload)

        metric_val = value_extractor(payload)
        window_start = self._get_window_start_epoch(msg.timestamp)

        window_id = (window_start, group_key)
        if window_id not in self._windows:
            self._windows[window_id] = []

        self._windows[window_id].append(metric_val)

    def emit_closed_windows(self, watermark_dt: datetime, metric_name: str = "metric") -> List[WindowResult]:
        """
        Emit results for windows older than the watermark timestamp.
        """
        watermark_epoch = self._get_window_start_epoch(watermark_dt)
        results: List[WindowResult] = []
        expired_keys = []

        for (w_start, g_key), values in self._windows.items():
            if w_start < watermark_epoch:
                w_start_dt = datetime.fromtimestamp(w_start, tz=timezone.utc)
                w_end_dt = w_start_dt + timedelta(seconds=self.window_size_sec)
                count = len(values)
                sum_val = sum(values)

                res = WindowResult(
                    window_start=w_start_dt,
                    window_end=w_end_dt,
                    group_key=g_key,
                    metric_name=metric_name,
                    count=count,
                    sum_val=sum_val,
                    avg_val=sum_val / count if count > 0 else 0.0,
                    min_val=min(values) if values else 0.0,
                    max_val=max(values) if values else 0.0,
                )
                results.append(res)
                expired_keys.append((w_start, g_key))

        # Evict processed windows
        for k in expired_keys:
            del self._windows[k]

        return results


class StreamProcessor:
    """
    Real-Time Event Stream Processor.

    Applies pipeline stages:
    1. Filter: Filter events by condition
    2. Transform / Enrich: Add extra calculated fields
    3. Aggregate: Maintain tumbling window aggregates
    4. Alerting: Detect threshold violations
    """

    def __init__(
        self,
        window_size_sec: int = 60,
        alert_threshold: Optional[float] = None,
    ):
        self.aggregator = TumblingWindowAggregator(window_size_sec=window_size_sec)
        self.alert_threshold = alert_threshold
        self.processed_count = 0
        self.filtered_count = 0
        self.alerts_triggered = 0

    def process_sales_event(self, msg: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Process a sales event:
        - Filter out cancelled orders
        - Enrich with order size category (Small, Medium, Large, Enterprise)
        """
        self.processed_count += 1
        payload = msg.value.get("payload", msg.value)

        # 1. Filter: Skip cancelled orders
        if payload.get("event_type") == "cancelled":
            self.filtered_count += 1
            logger.debug("[StreamProcessor] Filtered cancelled order: %s", payload.get("order_id"))
            return None

        # 2. Enrich: Calculate order size category
        total_amount = float(payload.get("total_amount", 0.0))
        if total_amount >= 500.0:
            order_category = "Enterprise"
        elif total_amount >= 200.0:
            order_category = "Large"
        elif total_amount >= 50.0:
            order_category = "Medium"
        else:
            order_category = "Small"

        enriched_event = {
            **payload,
            "order_category": order_category,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "kafka_metadata": {
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
            }
        }

        # 3. Add to tumbling window aggregator (total revenue per region)
        self.aggregator.add_event(msg, value_extractor=lambda p: float(p.get("total_amount", 0.0)))

        return enriched_event

    def process_iot_telemetry(self, msg: ProcessedMessage) -> Optional[Dict[str, Any]]:
        """
        Process an IoT sensor telemetry event:
        - Alert if value > alert_threshold
        - Add to sensor tumbling window aggregator
        """
        self.processed_count += 1
        payload = msg.value.get("payload", msg.value)

        sensor_val = float(payload.get("value", 0.0))
        alert_triggered = False

        if self.alert_threshold is not None and sensor_val > self.alert_threshold:
            alert_triggered = True
            self.alerts_triggered += 1
            logger.warning(
                "[STREAM ALERT] High sensor reading! device_id=%s type=%s val=%.2f threshold=%.2f",
                payload.get("device_id"), payload.get("sensor_type"), sensor_val, self.alert_threshold
            )

        enriched_event = {
            **payload,
            "stream_alert": alert_triggered,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.aggregator.add_event(msg, value_extractor=lambda p: float(p.get("value", 0.0)))
        return enriched_event

    def emit_aggregations(self, current_time: Optional[datetime] = None) -> List[WindowResult]:
        """Trigger window emission for windows older than current_time."""
        watermark = current_time or datetime.now(timezone.utc)
        return self.aggregator.emit_closed_windows(watermark_dt=watermark, metric_name="sum_amount")
