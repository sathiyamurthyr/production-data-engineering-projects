"""
Auto Loader CloudFiles for Enterprise Databricks

Production patterns for incremental data ingestion.
"""

from typing import Any


def autoloader_csv(
    spark: Any,
    source_path: str,
    table_name: str,
    schema_location: str = "/tmp/schema",
) -> Any:
    """
    Ingest CSV files using Auto Loader.
    
    Business Use Case: Incremental file ingestion from landing zone.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", schema_location)
        .option("header", "true")
        .load(source_path)
        .writeStream.format("delta")
        .outputMode("append")
        .table(table_name)
    )


def autoloader_json(
    spark: Any,
    source_path: str,
    table_name: str,
    schema_location: str = "/tmp/schema",
) -> Any:
    """
    Ingest JSON files using Auto Loader.
    
    Business Use Case: API event ingestion.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", schema_location)
        .option("cloudFiles.inferColumnTypes", "true")
        .load(source_path)
        .writeStream.format("delta")
        .outputMode("append")
        .option("mergeSchema", "true")
        .table(table_name)
    )


def autoloader_with_quarantine(
    spark: Any,
    source_path: str,
    valid_table: str,
    invalid_table: str,
) -> Any:
    """
    Ingest with quarantine for bad records.
    
    Business Use Case: Data quality enforcement.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("badRecordsPath", f"/tmp/bad_records/{invalid_table}")
        .load(source_path)
        .writeStream.format("delta")
        .outputMode("append")
        .queryName(f"quarantine_{invalid_table}")
        .table(invalid_table)
    )