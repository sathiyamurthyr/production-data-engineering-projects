# Python Coding Standards

## Overview

This document outlines the Python coding standards for the Production Data Engineering Projects repository. Following these standards ensures code quality, maintainability, and consistency across all projects.

## Style Guide

### PEP 8 Compliance

All Python code must follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines:

- Use 4 spaces for indentation (no tabs)
- Maximum line length of 100 characters
- Use blank lines to separate logical sections
- Use trailing commas in multi-line structures
- Use spaces around operators and after commas

### Naming Conventions

| Entity | Convention | Example |
|--------|------------|---------|
| Variables | `snake_case` | `user_name`, `data_frame` |
| Functions | `snake_case` | `validate_data()`, `process_batch()` |
| Classes | `PascalCase` | `DataValidator`, `ETLJob` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `BATCH_SIZE` |
| Modules | `snake_case` | `data_validator.py`, `etl_job.py` |
| Packages | `snake_case` | `data_quality/`, `streaming/` |

### Type Hints

Use type hints for all function arguments and return values:

```python
from typing import Any

def process_data(data: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Process data according to configuration."""
    return data
```

### Docstrings

Use Google-style docstrings for all public modules, functions, classes, and methods:

```python
def calculate_metrics(
    data: pd.DataFrame,
    metrics: list[str]
) -> dict[str, float]:
    """Calculate specified metrics from data.

    Args:
        data: Input DataFrame containing the data to analyze.
        metrics: List of metric names to calculate.

    Returns:
        Dictionary mapping metric names to calculated values.

    Raises:
        ValueError: If data is empty or metrics list is None.

    Example:
        >>> df = pd.DataFrame({"values": [1, 2, 3]})
        >>> result = calculate_metrics(df, ["mean", "std"])
        >>> print(result)
        {"mean": 2.0, "std": 1.0}
    """
    if data.empty:
        raise ValueError("Data cannot be empty")
```

## Best Practices

### Error Handling

1. **Be Specific**: Catch specific exceptions rather than generic `Exception`
2. **Context**: Include context in error messages
3. **Logging**: Log errors appropriately
4. **Cleanup**: Use context managers for resource cleanup

```python
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def database_connection(connection_string: str):
    """Context manager for database connections."""
    conn = None
    try:
        conn = create_connection(connection_string)
        yield conn
    except ConnectionError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    finally:
        if conn:
            conn.close()
```

### Logging

Use structured logging with appropriate log levels:

```python
import logging
import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info("processing_started", batch_size=1000, source="database")
logger.error("validation_failed", error=str(e), record_id=record.id)
```

### Configuration Management

Never hardcode values. Use Pydantic for configuration:

```python
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = Field(..., env="DATABASE_URL")
    batch_size: int = Field(default=1000, env="BATCH_SIZE")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
```

### Testing

All code must have comprehensive tests:

```python
import pytest
from pytest import fixture

@fixture
def sample_data() -> pd.DataFrame:
    """Create sample data for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
    })

def test_process_data(sample_data: pd.DataFrame) -> None:
    """Test that process_data handles valid input correctly."""
    result = process_data(sample_data)
    assert len(result) == len(sample_data)
```

## Tools

### Black

Configuration in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ["py313"]
```

### Ruff

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", "TCH"]
```

### MyPy

Run MyPy for static type checking:

```bash
mypy projects/ --strict
```

## Common Patterns

### Factory Pattern

```python
from abc import ABC, abstractmethod
from typing import Any

class DataExtractor(ABC):
    """Abstract base class for data extractors."""

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Extract data from source."""
        ...

class DatabaseExtractor(DataExtractor):
    """Extract data from database."""

    def extract(self) -> pd.DataFrame:
        """Extract data from database connection."""
        # Implementation
        ...

def create_extractor(source_type: str, **kwargs: Any) -> DataExtractor:
    """Factory function to create extractors."""
    extractors = {
        "database": DatabaseExtractor,
        "api": APIExtractor,
        "file": FileExtractor,
    }
    extractor_class = extractors.get(source_type)
    if not extractor_class:
        raise ValueError(f"Unknown source type: {source_type}")
    return extractor_class(**kwargs)
```

### Retry Pattern

```python
import time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (ConnectionError,),
) -> Callable[..., T]:
    """Decorator for retrying functions with exponential backoff."""
    def wrapper(*args: Any, **kwargs: Any) -> T:
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if attempt == max_retries - 1:
                    raise
                wait = backoff_factor ** attempt
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(wait)
    return wrapper
```

### Context Manager Pattern

```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def spark_session(
    app_name: str,
    config: dict[str, str] | None = None
) -> Generator[SparkSession, None, None]:
    """Context manager for Spark session lifecycle."""
    builder = SparkSession.builder.appName(app_name)
    if config:
        for key, value in config.items():
            builder.config(key, value)

    spark = builder.getOrCreate()
    try:
        yield spark
    finally:
        spark.stop()
```

## Do's and Don'ts

### Do's ✅

- [ ] Use type hints for all functions
- [ ] Write comprehensive docstrings
- [ ] Handle exceptions gracefully
- [ ] Use logging instead of print
- [ ] Write unit and integration tests
- [ ] Use context managers for resources
- [ ] Follow SOLID principles
- [ ] Keep functions small and focused

### Don'ts ❌

- [ ] Don't hardcode values
- [ ] Don't ignore exceptions silently
- [ ] Don't use print statements in production code
- [ ] Don't commit secrets or credentials
- [ ] Don't write untested code
- [ ] Don't use mutable default arguments
- [ ] Don't use global state unnecessarily
- [ ] Don't mix concerns in single functions