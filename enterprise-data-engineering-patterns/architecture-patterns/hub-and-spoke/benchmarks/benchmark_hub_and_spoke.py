"""Benchmarks for the Hub-and-Spoke pattern."""

from __future__ import annotations

import time

from src.hub_and_spoke import HubAndSpoke


def benchmark_execute() -> None:
    """Benchmark the execute method."""
    pattern = HubAndSpoke()
    data = "sample_data"

    start = time.perf_counter()
    for _ in range(1000):
        pattern.execute(data)
    elapsed = time.perf_counter() - start

    print(f"1000 executions: {elapsed:.4f}s ({elapsed/1000*1000:.2f}ms per call)")


if __name__ == "__main__":
    benchmark_execute()
