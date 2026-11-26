"""
Module 26-30: Strict Typing, Decorators, Generators, Iterators, and Context Managers.

Explanation:
- Generators: Yield records line-by-line avoiding OOM (Out-of-Memory) on multi-GB files.
- Decorators: Enforce retry logic, timing benchmarks, and authentication wrappers.
- Context Managers: Manage DB connections, lock files, and temporary directories.

Business Use Case:
Implement a memory-efficient generator function with an automated retry decorator.
"""

import time
import functools
import logging
from typing import Generator, Callable, Any, List

logger = logging.getLogger(__name__)

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retry logic on transient pipeline failures."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.warning(f"Attempt {attempts}/{max_attempts} failed for {func.__name__}: {e}")
                    if attempts == max_attempts:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator

def batch_stream_generator(data: List[Any], batch_size: int = 2) -> Generator[List[Any], None, None]:
    """Generator yielding memory-safe micro-batches."""
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]
