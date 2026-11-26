"""
================================================================================
MODULE 29: Iterators & Custom Iteration Protocols
================================================================================
1. EXPLANATION:
Classes implementing `__iter__()` and `__next__()` form custom iterators for data batches.

2. BUSINESS USE CASE:
Implement a custom batch reader iterator over a dataset.
"""
class BatchReader:
    """Custom Batch Iterator."""
    def __init__(self, data: list, batch_size: int = 2) -> None:
        self.data = data
        self.batch_size = batch_size
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.data):
            raise StopIteration
        batch = self.data[self.index:self.index + self.batch_size]
        self.index += self.batch_size
        return batch

if __name__ == "__main__":
    reader = BatchReader([10, 20, 30, 40, 50], batch_size=2)
    for b in reader:
        print("Read Batch:", b)
