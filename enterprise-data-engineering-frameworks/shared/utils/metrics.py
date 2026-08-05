"""Metrics collection utilities."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metric:
    name: str
    value: float
    unit: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """Thread-safe metrics registry."""
    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: float = 1, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, tags: dict | None = None) -> None:
        self._gauges[self._key(name, tags)] = value

    def histogram(self, name: str, value: float, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    @contextmanager
    def timer(self, name: str, tags: dict | None = None):
        start = time.perf_counter()
        yield
        self.histogram(name, time.perf_counter() - start, tags)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: {"count": len(v), "sum": sum(v), "avg": sum(v) / len(v) if v else 0} for k, v in self._histograms.items()},
        }

    @staticmethod
    def _key(name: str, tags: dict | None) -> str:
        if not tags:
            return name
        return f"{name}|{','.join(f'{k}={v}' for k, v in sorted(tags.items()))}"


metrics = MetricsRegistry()

