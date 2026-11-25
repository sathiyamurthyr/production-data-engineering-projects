"""
================================================================================
MODULE 27: Decorators for Profiling & Retry Mechanics
================================================================================
1. EXPLANATION:
Decorators wrap functions to add cross-cutting behavior like timing execution and automated retries.

2. BUSINESS USE CASE:
Benchmark pipeline execution duration using `@timeit`.
"""
import time
import functools
import logging

logger = logging.getLogger("m27_decorators")

def timeit(func):
    """Decorator to measure function execution runtime."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"Function '{func.__name__}' executed in {elapsed:.4f} seconds.")
        return result
    return wrapper

@timeit
def heavy_transformation(count: int) -> int:
    return sum(i * i for i in range(count))

if __name__ == "__main__":
    heavy_transformation(100000)
