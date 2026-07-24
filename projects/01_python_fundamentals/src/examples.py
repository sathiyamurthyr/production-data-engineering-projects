"""Python examples for data engineering fundamentals.

This module contains production-ready examples for:
- Variables and Data Types
- Operators
- Strings
- Lists, Tuples, Sets, Dictionaries
- Loops and Functions
- Lambda and List Comprehension
- Exception Handling
- File Handling (CSV, JSON)
- DateTime operations
- Logging patterns
- Environment Variables
- Virtual Environment
- Modules and Packages
- OOP and Dataclasses
- Typing
- Decorators
- Generators and Iterators
- Context Managers
- Regular Expressions
- API Requests
- SQLite
- Pandas Basics
- Data Cleaning
- CLI Arguments
- OS Module
- Pathlib
- Subprocess
- Unit Testing
- Mock Testing
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

# =============================================================================
# 01 Variables - Data Engineering Context
# =============================================================================
"""
In data engineering, variables store:
- Configuration values
- File paths
- Database connection strings
- Processing parameters
"""
batch_size: int = 1000
data_source: str = "s3://bucket/data/"
is_production: bool = False


# =============================================================================
# 02 Data Types - Essential for Data Processing
# =============================================================================
def demonstrate_data_types() -> dict:
    """Demonstrate Python data types with data engineering context."""
    # Integer - record counts, IDs
    record_count: int = 50000

    # Float - metrics, timestamps
    processing_time: float = 12.5

    # String - file paths, query strings
    query: str = "SELECT * FROM customers WHERE active = true"

    # Boolean - flags for processing logic
    is_valid: bool = True

    # None - missing data handling
    last_run: None = None

    return {
        "record_count": record_count,
        "processing_time": processing_time,
        "query": query,
        "is_valid": is_valid,
        "last_run": last_run,
    }


# =============================================================================
# 03 Operators - For Data Filtering and Transformation
# =============================================================================
def filter_by_age(age: int, min_age: int = 18) -> bool:
    """Use comparison operators for data filtering."""
    return age >= min_age


def calculate_percentile(value: float, total: float) -> float:
    """Use arithmetic operators for metrics calculation."""
    if total == 0:
        return 0.0
    return (value / total) * 100


# =============================================================================
# 04 Strings - Essential for Data Processing
# =============================================================================
def clean_column_name(column: str) -> str:
    """Clean column names for data pipelines.

    Business Use Case: Standardizing column names from various sources
    """
    # Lowercase and replace spaces with underscores
    cleaned = column.lower().strip().replace(" ", "_")
    # Remove special characters
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
    return cleaned


def extract_domain(email: str) -> str:
    """Extract domain from email address.

    Business Use Case: Email domain analysis for customer segmentation
    """
    return email.split("@")[-1] if "@" in email else ""


# =============================================================================
# 05 Lists - Core Data Structure for Collections
# =============================================================================
def process_batch(records: list[dict]) -> list[dict]:
    """Process a batch of records.

    Business Use Case: Batch processing in ETL pipelines
    """
    # List comprehension for filtering
    valid_records = [r for r in records if r.get("status") == "active"]

    # Sort by timestamp
    sorted_records = sorted(valid_records, key=lambda x: x.get("timestamp", ""))

    return sorted_records


def chunk_list(data: list, chunk_size: int = 100) -> list[list]:
    """Split large list into chunks for batch processing.

    Business Use Case: Memory-efficient batch processing
    """
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


# =============================================================================
# 06 Tuples - Immutable Data for Configuration
# =============================================================================
# Column order for database insertion (immutable)
CUSTOMER_COLUMNS: tuple[str, ...] = (
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "signup_date",
    "country",
    "age",
)

# Database connection parameters (immutable)
DB_CONFIG: tuple[str, str, str] = ("localhost", "5432", "analytics")


# =============================================================================
# 07 Sets - For Deduplication and Membership Testing
# =============================================================================
def find_duplicate_emails(customers: list[dict]) -> set[str]:
    """Find duplicate emails in customer data.

    Business Use Case: Data quality check for deduplication
    """
    emails = [c["email"] for c in customers]
    return {email for email in emails if emails.count(email) > 1}


def validate_countries(
    customer_countries: list[str], valid_countries: set[str]
) -> set[str]:
    """Find invalid countries.

    Business Use Case: Data validation against reference data
    """
    return {country for country in set(customer_countries) if country not in valid_countries}


# =============================================================================
# 08 Dictionaries - Key-Value Storage for Records
# =============================================================================
def aggregate_metrics(records: list[dict]) -> dict[str, float]:
    """Aggregate metrics from records.

    Business Use Case: Computing summary statistics
    """
    if not records:
        return {}

    total_revenue = sum(r.get("revenue", 0) for r in records)
    avg_age = sum(r.get("age", 0) for r in records) / len(records)

    return {"total_revenue": total_revenue, "avg_age": avg_age}


def merge_configs(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Merge configuration dictionaries.

    Business Use Case: Configuration layering (default + environment)
    """
    return {**base, **override}


# =============================================================================
# 09 Loops - Essential for Data Processing
# =============================================================================
def process_files(directory: Path) -> int:
    """Process all CSV files in directory.

    Business Use Case: Batch file processing
    """
    total_rows = 0
    for file_path in directory.glob("*.csv"):
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            total_rows += sum(1 for _ in reader)
    return total_rows


def exponential_backoff(attempt: int, base_delay: float = 1.0) -> float:
    """Calculate backoff delay with jitter.

    Business Use Case: Retry logic for API calls
    """
    delay = base_delay * (2**attempt)
    return min(delay, 60)  # Cap at 60 seconds


# =============================================================================
# 10 Functions - Modular Data Processing
# =============================================================================
def validate_schema(data: dict, expected_keys: set[str]) -> bool:
    """Validate data schema.

    Business Use Case: Schema validation in ETL pipelines
    """
    return set(data.keys()) == expected_keys


# =============================================================================
# 11 Lambda - For Inline Transformations
# =============================================================================
# Common data transformations
extract_id = lambda record: record.get("id")
calculate_score = lambda record: record.get("value", 0) * 1.5
is_valid_email = lambda email: "@" in email and "." in email


# =============================================================================
# 12 List Comprehension - Efficient Data Filtering
# =============================================================================
def filter_active_customers(customers: list[dict]) -> list[dict]:
    """Filter active customers using list comprehension.

    Business Use Case: Data filtering for downstream processing
    """
    return [c for c in customers if c.get("status") == "active" and c.get("age", 0) >= 18]


def extract_columns(records: list[dict], columns: list[str]) -> list[dict]:
    """Extract specific columns from records.

    Business Use Case: Column selection in ETL
    """
    return [{col: record[col] for col in columns if col in record} for record in records]


# =============================================================================
# 13 Exception Handling - Production Error Management
# =============================================================================
def safe_read_csv(file_path: Path) -> list[dict] | None:
    """Safely read CSV with error handling.

    Business Use Case: Graceful handling of corrupted files
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except csv.Error as e:
        print(f"CSV parsing error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# =============================================================================
# 14 File Handling - Core Data Engineering Operations
# =============================================================================
def read_large_csv(file_path: Path, chunk_size: int = 1000) -> Generator[list[dict], None, None]:
    """Read large CSV in chunks.

    Business Use Case: Memory-efficient processing of large files
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def write_json(data: list[dict], output_path: Path) -> None:
    """Write data to JSON file.

    Business Use Case: Exporting processed data
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# =============================================================================
# 15 JSON - API and Configuration Handling
# =============================================================================
def parse_api_response(response_text: str) -> dict:
    """Parse JSON API response.

    Business Use Case: Processing REST API data
    """
    return json.loads(response_text)


def flatten_json(nested: dict, parent_key: str = "", sep: str = "_") -> dict:
    """Flatten nested JSON structure.

    Business Use Case: Normalizing nested API responses
    """
    items = {}
    for key, value in nested.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_json(value, new_key, sep))
        else:
            items[new_key] = value
    return items


# =============================================================================
# 16 DateTime - Time Series Processing
# =============================================================================
def get_date_range(days_back: int = 30) -> tuple[datetime, datetime]:
    """Get date range for incremental processing.

    Business Use Case: Incremental data loading
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO format.

    Business Use Case: Standardizing timestamps
    """
    return dt.isoformat()


# =============================================================================
# 17 Logging - Production Observability
# =============================================================================
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get structured logger for data pipeline.

    Business Use Case: Production logging for debugging
    """
    return structlog.get_logger(name)


# =============================================================================
# 18 Config Files - Externalized Configuration
# =============================================================================
def load_config(config_path: Path) -> dict:
    """Load YAML configuration file.

    Business Use Case: Environment-specific configuration
    """
    import yaml

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# =============================================================================
# 19 Environment Variables - Secure Configuration
# =============================================================================
def get_env_var(name: str, default: str | None = None) -> str:
    """Get environment variable with error handling.

    Business Use Case: Secure secrets management
    """
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Required environment variable {name} not set")
    return value


# =============================================================================
# 20 Virtual Environment - Dependency Isolation
# =============================================================================
# This is a conceptual example - venv is created via CLI:
# python -m venv .venv && source .venv/bin/activate


# =============================================================================
# 21 Modules - Code Organization
# =============================================================================
# This file is a module - demonstrating proper organization


# =============================================================================
# 22 Packages - Larger Code Organization
# =============================================================================
# Package structure:
# src/
#   __init__.py
#   config.py
#   logger.py
#   models.py
#   main.py


# =============================================================================
# 23 OOP - Object-Oriented Data Processing
# =============================================================================
class ETLProcessor:
    """Base ETL processor class.

    Business Use Case: Reusable ETL framework
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._processed_count = 0

    @property
    def processed_count(self) -> int:
        """Return count of processed records."""
        return self._processed_count

    def extract(self) -> list[dict]:
        """Extract data - to be overridden."""
        raise NotImplementedError

    def transform(self, data: list[dict]) -> list[dict]:
        """Transform data - to be overridden."""
        raise NotImplementedError

    def load(self, data: list[dict]) -> None:
        """Load data - to be overridden."""
        raise NotImplementedError

    def run(self) -> None:
        """Execute full ETL pipeline."""
        data = self.extract()
        transformed = self.transform(data)
        self.load(transformed)


# =============================================================================
# 24 Dataclasses - Clean Data Models
# =============================================================================
@dataclass
class ProcessingStats:
    """Statistics for data processing.

    Business Use Case: Tracking pipeline metrics
    """

    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100

    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "failed_records": self.failed_records,
            "success_rate": self.success_rate,
            "start_time": self.start_time.isoformat(),
        }


# =============================================================================
# 25 Typing - Type Safety for Production Code
# =============================================================================
def process_data[T](data: list[T], transformer: callable) -> list[T]:
    """Generic function for data transformation.

    Business Use Case: Type-safe reusable transformations
    """
    return [transformer(item) for item in data]


# =============================================================================
# 26 Decorators - Cross-Cutting Concerns
# =============================================================================
def log_execution(func: callable) -> callable:
    """Decorator to log function execution.

    Business Use Case: Automatic logging for pipeline steps
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__name__)
        logger.info(f"Starting {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Completed {func.__name__}")
        return result

    return wrapper


# =============================================================================
# 27 Generators - Memory Efficient Processing
# =============================================================================
def batch_generator(records: list[dict], batch_size: int = 100) -> Generator[list[dict], None, None]:
    """Generate batches of records.

    Business Use Case: Processing large datasets without memory issues
    """
    for i in range(0, len(records), batch_size):
        yield records[i : i + batch_size]


# =============================================================================
# 28 Iterators - Custom Iteration Logic
# =============================================================================
class BatchIterator:
    """Custom iterator for batch processing.

    Business Use Case: Custom batch iteration logic
    """

    def __init__(self, data: list, batch_size: int = 100):
        self.data = data
        self.batch_size = batch_size
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self) -> list:
        if self.index >= len(self.data):
            raise StopIteration
        batch = self.data[self.index : self.index + self.batch_size]
        self.index += self.batch_size
        return batch


# =============================================================================
# 29 Context Managers - Resource Management
# =============================================================================
@contextmanager
def database_connection(connection_string: str):
    """Context manager for database connections.

    Business Use Case: Safe database connection handling
    """
    conn = sqlite3.connect(connection_string)
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# 30 Regular Expressions - Data Cleaning
# =============================================================================
def clean_phone(phone: str) -> str:
    """Clean phone number format.

    Business Use Case: Phone number standardization
    """
    digits = re.sub(r"\D", "", phone)
    return f"+1-{digits[-10:-7]}-{digits[-7:-4]}-{digits[-4:]}" if len(digits) >= 10 else ""


def validate_email(email: str) -> bool:
    """Validate email format.

    Business Use Case: Email data quality check
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{{2,}}$"
    return bool(re.match(pattern, email))


# =============================================================================
# 31 API Requests - External Data Sources
# =============================================================================
def fetch_api_data(url: str, timeout: int = 30) -> dict:
    """Fetch data from REST API with retry logic.

    Business Use Case: Integrating external APIs
    """
    import time

    for attempt in range(3):
        try:
            import requests

            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == 2:
                raise
            time.sleep(exponential_backoff(attempt))
    return {}


# =============================================================================
# 32 REST API - Building Data Services
# =============================================================================
def create_health_endpoint() -> dict:
    """Create health check response.

    Business Use Case: Health checks for data services
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


# =============================================================================
# 33 SQLite - Embedded Database for Pipelines
# =============================================================================
def create_staging_table(db_path: str) -> None:
    """Create staging table for data pipeline.

    Business Use Case: Local data staging
    """
    with database_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS staging_customers (
                customer_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                signup_date DATE,
                processed_at TIMESTAMP
            )
        """)
        conn.commit()


# =============================================================================
# 34 Pandas Basics - Data Analysis Foundation
# =============================================================================
def load_dataframe(file_path: Path) -> "pandas.DataFrame":
    """Load data into DataFrame.

    Business Use Case: Pandas-based data processing
    """
    import pandas as pd

    return pd.read_csv(file_path)


def aggregate_by_country(df: "pandas.DataFrame") -> "pandas.DataFrame":
    """Aggregate customer counts by country.

    Business Use Case: Business metrics calculation
    """
    return df.groupby("country").size().reset_index(name="customer_count")


# =============================================================================
# 35 Data Cleaning - Production Quality
# =============================================================================
def clean_dataframe(df: "pandas.DataFrame") -> "pandas.DataFrame":
    """Clean DataFrame for analysis.

    Business Use Case: Production data cleaning
    """
    # Remove duplicates
    df = df.drop_duplicates()

    # Fill missing values
    df = df.fillna({"age": df["age"].median()})

    # Strip whitespace
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    return df


# =============================================================================
# 36 Command Line Arguments - CLI Tools
# =============================================================================
def parse_cli_args() -> dict:
    """Parse command line arguments.

    Business Use Case: CLI configuration for pipelines
    """
    import argparse

    parser = argparse.ArgumentParser(description="ETL Pipeline")
    parser.add_argument("--config", default="configs/dev.yaml")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    return {"config": args.config, "batch_size": args.batch_size, "dry_run": args.dry_run}


# =============================================================================
# 37 OS Module - System Operations
# =============================================================================
def check_disk_space(path: Path) -> dict:
    """Check disk space for data processing.

    Business Use Case: Storage monitoring
    """
    import shutil

    total, used, free = shutil.disk_usage(path)
    return {
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
    }


# =============================================================================
# 38 Pathlib - Modern File Path Handling
# =============================================================================
def find_latest_file(directory: Path, pattern: str = "*.csv") -> Path | None:
    """Find latest file matching pattern.

    Business Use Case: Incremental file processing
    """
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


# =============================================================================
# 39 Subprocess - Running External Commands
# =============================================================================
def run_spark_job(script_path: Path) -> int:
    """Run Spark job via subprocess.

    Business Use Case: Orchestrating Spark jobs
    """
    result = subprocess.run(
        ["spark-submit", str(script_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode


# =============================================================================
# 40 Unit Testing - Testable Code
# =============================================================================
def calculate_average(values: list[float]) -> float:
    """Calculate average with proper error handling.

    Business Use Case: Metric calculations in pipelines
    """
    if not values:
        raise ValueError("Cannot calculate average of empty list")
    return sum(values) / len(values)


# =============================================================================
# 41 Mock Testing - Isolated Tests
# =============================================================================
def fetch_external_data(url: str) -> list[dict]:
    """Fetch data from external source.

    Business Use Case: External data integration
    """
    import requests

    response = requests.get(url)
    return response.json()


# =============================================================================
# 42 Logging Best Practices - Production Observability
# =============================================================================
def log_pipeline_step(step: str, record_count: int, duration_ms: float) -> None:
    """Log pipeline step with metrics.

    Business Use Case: Pipeline monitoring
    """
    logger = get_logger("pipeline")
    logger.info(
        "pipeline_step_completed",
        step=step,
        record_count=record_count,
        duration_ms=duration_ms,
    )


# =============================================================================
# 43 Configuration Management - Externalized Config
# =============================================================================
def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value with fallback.

    Business Use Case: Flexible configuration
    """
    return get_setting(key, default)


# =============================================================================
# 44 Mini ETL Project - Complete Pipeline Example
# =============================================================================
def mini_etl_pipeline(input_path: Path, output_path: Path) -> dict:
    """Complete mini ETL pipeline example.

    Business Use Case: End-to-end data processing
    """
    import pandas as pd

    # Extract
    df = pd.read_csv(input_path)

    # Transform
    df_clean = clean_dataframe(df)

    # Load
    df_clean.to_json(output_path, orient="records")

    return {
        "input_records": len(df),
        "output_records": len(df_clean),
        "output_path": str(output_path),
    }


# Need to import Any for typing
from typing import Any


# Need to import structlog for logging
import structlog