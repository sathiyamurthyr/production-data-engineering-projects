"""Retry engine with multiple backoff strategies."""
from __future__ import annotations
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any
from shared.exceptions import RetryExhaustedError

class BackoffStrategy(Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"

@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

class RetryEngine:
    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        attempt = 0
        last_error = None
        while attempt < self.config.max_attempts:
            try:
                return func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_error = e
                attempt += 1
                if attempt >= self.config.max_attempts:
                    break
                time.sleep(self._calc_delay(attempt))
        raise RetryExhaustedError(f"Failed after {self.config.max_attempts} attempts", details={"last_error": str(last_error)})
    def _calc_delay(self, attempt: int) -> float:
        if self.config.backoff == BackoffStrategy.FIXED:
            return min(self.config.initial_delay, self.config.max_delay)
        elif self.config.backoff == BackoffStrategy.LINEAR:
            return min(self.config.initial_delay * attempt, self.config.max_delay)
        elif self.config.backoff == BackoffStrategy.EXPONENTIAL:
            return min(self.config.initial_delay * (2**(attempt-1)), self.config.max_delay)
        elif self.config.backoff == BackoffStrategy.EXPONENTIAL_JITTER:
            import random
            base = self.config.initial_delay * (2**(attempt-1))
            return min(base + random.uniform(0, base*0.1), self.config.max_delay)
        return self.config.initial_delay

