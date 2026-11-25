"""
================================================================================
MODULE 28: Generators & Memory-Safe Streaming
================================================================================
1. EXPLANATION:
Generators (`yield`) produce records on demand without loading full files into memory, preventing OOMs.

2. BUSINESS USE CASE:
Read multi-gigabyte files line-by-line using generators.
"""
from typing import Generator

def stream_numbers(total: int) -> Generator[int, None, None]:
    """Stream numbers sequentially."""
    for i in range(total):
        yield i

if __name__ == "__main__":
    stream = stream_numbers(5)
    for val in stream:
        print("Streamed value:", val)
