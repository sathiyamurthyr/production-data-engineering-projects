"""Metrics collection utilities for data engineering patterns.

Provides a MetricsCollector class for tracking performance, reliability,
and business metrics in a structured way.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """A single metric measurement."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = "count"


@dataclass
class Counter:
    """A counter metric that only goes up."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)

    def increment(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class Gauge:
    """A gauge metric that can go up and down."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Timer:
    """A timer for measuring execution time."""

    name: str
    start: float = field(default_factory=time.perf_counter)
    labels: dict[str, str] = field(default_factory=dict)

    def stop(self) -> float:
        elapsed = time.perf_counter() - self.start
        logger.info(
            "Timer stopped",
            timer_name=self.name,
            elapsed_seconds=elapsed,
        )
        return elapsed


class MetricsCollector:
    """Collects and aggregates metrics for pattern execution.

    Usage:
        >>> collector = MetricsCollector()
        >>> timer = collector.start_timer("processing")
        >>> # ... do work ...
        >>> elapsed = timer.stop()
        >>> collector.increment_counter("records_processed", value=100)
        >>> collector.set_gauge("queue_depth", value=42)
        >>> collector.flush()
    """

    def __init__(self, pattern_name: str = "unknown") -> None:
        self.pattern_name = pattern_name
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._metrics: list[Metric] = []
        self._timers: dict[str, Timer] = {}

    def increment_counter(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name.
            value: Amount to increment by.
            **labels: Label dimensions for the metric.
        """
        if name not in self._counters:
            self._counters[name] = Counter(name=name, labels=labels)
        self._counters[name].increment(value)

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        """Set a gauge metric value.

        Args:
            name: Gauge name.
            value: Gauge value.
            **labels: Label dimensions.
        """
        self._gauges[name] = Gauge(name=name, value=value, labels=labels)

    def start_timer(self, name: str, **labels: str) -> Timer:
        """Start a timer and return it.

        Args:
            name: Timer name.
            **labels: Label dimensions.

        Returns:
            Timer instance to call .stop() on.
        """
        timer = Timer(name=name, labels=labels)
        self._timers[name] = timer
        return timer

    def record(self, name: str, value: float, unit: str = "count", **labels: str) -> None:
        """Record a raw metric.

        Args:
            name: Metric name.
            value: Metric value.
            unit: Unit of measurement.
            **labels: Label dimensions.
        """
        self._metrics.append(
            Metric(name=name, value=value, labels=labels, unit=unit)
        )

    def get_all_metrics(self) -> list[dict[str, Any]]:
        """Get all collected metrics as dictionaries.

        Returns:
            List of metric dictionaries.
        """
        results: list[dict[str, Any]] = []

        for counter in self._counters.values():
            results.append(
                {
                    "name": counter.name,
                    "value": counter.value,
                    "type": "counter",
                    "labels": counter.labels,
                }
            )

        for gauge in self._gauges.values():
            results.append(
                {
                    "name": gauge.name,
                    "value": gauge.value,
                    "type": "gauge",
                    "labels": gauge.labels,
                }
            )

        for timer_name, timer in self._timers.items():
            results.append(
                {
                    "name": timer_name,
                    "value": 0.0,
                    "type": "timer",
                    "labels": timer.labels,
                }
            )

        for metric in self._metrics:
            results.append(
                {
                    "name": metric.name,
                    "value": metric.value,
                    "type": "metric",
                    "unit": metric.unit,
                    "labels": metric.labels,
                }
            )

        return results

    def flush(self) -> None:
        """Log all collected metrics and reset counters."""
        metrics = self.get_all_metrics()
        logger.info(
            "Metrics flushed",
            pattern=self.pattern_name,
            total_metrics=len(metrics),
            metrics=metrics,
        )
        self._counters.clear()
        self._gauges.clear()
        self._metrics.clear()
        self._timers.clear()
