"""Benchmarks for the Hexagonal Architecture pattern."""

from __future__ import annotations

import time

from src.hexagonal_architecture import HexagonalArchitecture


def benchmark_execute() -> None:
    """Benchmark the execute method."""
    pattern = HexagonalArchitecture()
    data = "sample_data"

    start = time.perf_counter()
    for _ in range(1000):
        pattern.execute(data)
    elapsed = time.perf_counter() - start

    print(f"1000 executions: {elapsed:.4f}s ({elapsed/1000*1000:.2f}ms per call)")


if __name__ == "__main__":
    benchmark_execute()
