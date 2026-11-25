"""
Hard Level Data Engineering Exercises.

Exercise 3: Implement a memory-efficient line generator that reads a large file micro-batch by micro-batch,
yields valid JSON rows, and logs bad rows.
"""
from pathlib import Path
from typing import Generator, List, Dict, Any

def microbatch_file_reader(file_path: Path, batch_size: int = 2) -> Generator[List[Dict[str, Any]], None, None]:
    """TODO for student: Implement microbatch generator."""
    pass
