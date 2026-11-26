"""
================================================================================
MODULE 05: Lists in High-Throughput Buffering
================================================================================

1. EXPLANATION:
--------------------------------------------------------------------------------
Lists are ordered, mutable dynamic arrays. In data engineering pipelines, lists buffer batch records
in memory before executing bulk database writes or bulk S3 multi-part uploads.

2. BUSINESS USE CASE:
--------------------------------------------------------------------------------
Buffer incoming event messages into micro-batches of size N before flushing to disk/database.

3. PRODUCTION EXAMPLE:
--------------------------------------------------------------------------------
Buffers stream records into fixed micro-batches and triggers flush events.

4. EXPECTED OUTPUT:
--------------------------------------------------------------------------------
[INFO] Flushed batch of 3 records to database.
"""

from typing import List, Any, Generator

def create_micro_batches(items: List[Any], batch_size: int = 3) -> Generator[List[Any], None, None]:
    """Chunk a list into fixed-size micro-batches."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

if __name__ == "__main__":
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    batches = list(create_micro_batches(data, batch_size=3))
    print("Generated Micro-Batches:", batches)
