"""
Production SparkSession Configuration for Data Engineering

Enterprise-grade Spark session management.
"""

from typing import Any


def create_spark_session(
    app_name: str = "DataEngineering",
    master: str = "local[*]",
    config: dict[str, Any] | None = None,
) -> Any:
    """
    Create production-ready SparkSession.
    
    Business Use Case: Enterprise ETL job configuration.
    """
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.adaptive.skewJoin.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
    )

    if config:
        for key, value in config.items():
            builder = builder.config(key, value)

    return builder.getOrCreate()


def get_spark_config(environment: str = "production") -> dict[str, Any]:
    """
    Get Spark configuration for environment.
    
    Business Use Case: Multi-environment deployment.
    """
    configs = {
        "development": {
            "spark.sql.shuffle.partitions": "4",
            "spark.sql.adaptive.enabled": "true",
        },
        "production": {
            "spark.sql.shuffle.partitions": "200",
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.sql.adaptive.skewJoin.enabled": "true",
            "spark.sql.adaptive.skewJoin.skewedPartitionFactor": "5",
            "spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes": "32MB",
        },
    }

    return configs.get(environment, configs["production"])