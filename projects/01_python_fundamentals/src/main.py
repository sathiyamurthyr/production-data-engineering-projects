"""Main entry point for Python Fundamentals project.

This demonstrates a complete ETL pipeline with production patterns.
"""

from pathlib import Path

from models import Customer, ETLJobConfig
from config import get_setting, load_yaml_config, settings
from logger import get_logger, setup_logging


def extract_csv_data(file_path: Path) -> list[dict]:
    """Extract data from CSV file.

    Args:
        file_path: Path to CSV file.

    Returns:
        List of row dictionaries.
    """
    import csv

    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def transform_customers(raw_data: list[dict]) -> list[Customer]:
    """Transform raw CSV data into validated Customer models.

    Args:
        raw_data: Raw customer data from CSV.

    Returns:
        List of validated Customer models.
    """
    customers = []
    for row in raw_data:
        customer = Customer(
            customer_id=int(row["customer_id"]),
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            signup_date=row["signup_date"],
            country=row["country"],
            age=int(row["age"]),
        )
        customers.append(customer)
    return customers


def load_to_json(customers: list[Customer], output_path: Path) -> None:
    """Load validated customers to JSON file.

    Args:
        customers: List of Customer models.
        output_path: Path to output JSON file.
    """
    import json

    data = [c.model_dump() for c in customers]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def run_etl_pipeline(config_path: Path) -> None:
    """Run complete ETL pipeline.

    This demonstrates:
    - Configuration management
    - Structured logging
    - Error handling
    - Data validation

    Args:
        config_path: Path to YAML configuration.
    """
    setup_logging(log_level=settings.log_level)
    logger = get_logger("main")

    logger.info("Starting ETL pipeline", config_path=str(config_path))

    try:
        config = load_yaml_config(config_path)
        job_config = ETLJobConfig(**config)

        # Extract
        raw_data = extract_csv_data(settings.data_directory / "customers.csv")
        logger.info("Extracted data", rows=len(raw_data))

        # Transform
        customers = transform_customers(raw_data)
        logger.info("Transformed data", customers=len(customers))

        # Load
        output_path = settings.data_directory.parent / "processed" / "customers.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        load_to_json(customers, output_path)
        logger.info("Loaded data", output_path=str(output_path))

    except Exception as e:
        logger.error("Pipeline failed", error=str(e))
        raise


if __name__ == "__main__":
    config_path = Path(__file__).parent.parent / "configs" / "dev.yaml"
    run_etl_pipeline(config_path)