"""
================================================================================
MODULE 30: Context Managers & Resource Management
================================================================================
1. EXPLANATION:
Context managers (`@contextmanager` or `__enter__`/`__exit__`) guarantee cleanup of database locks and files.

2. BUSINESS USE CASE:
Create a managed timer context manager for tracking ETL job steps.
"""
from contextlib import contextmanager
import time

@contextmanager
def timer(step_name: str):
    """Context manager timing a block execution."""
    start = time.perf_counter()
    print(f"Starting step [{step_name}]...")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"Step [{step_name}] finished in {elapsed:.4f}s")

if __name__ == "__main__":
    with timer("Extract CSV Data"):
        time.sleep(0.05)
