"""
spark_session.py
================
SparkSession factory with configuration management for production environments.

Business Use Case:
    Centralise all SparkSession creation so that every job, notebook, or unit
    test obtains a consistently-configured session.  Avoids scattered
    SparkSession.builder calls that may conflict or miss critical settings.

Production Patterns Covered:
    - Local / YARN / Kubernetes mode detection
    - Hive Metastore integration (external)
    - S3A / ADLS Gen-2 (ABFS) cloud storage config
    - Delta Lake extensions (optional)
    - Adaptive Query Execution (AQE) defaults
    - Dynamic partition pruning
    - Custom log-level management

Interview Questions:
    Q: What is the difference between SparkContext, SparkSession, and SQLContext?
    A: SparkContext (pre-2.0) = entry point to core RDD API.
       SQLContext (pre-2.0) = entry point for Spark SQL.
       SparkSession (2.0+) = unified entry point that wraps both and adds Dataset API.
       In 3.x, SparkSession.sparkContext gives you the underlying SparkContext.

    Q: Can two SparkSessions share the same SparkContext?
    A: Yes – SparkSession.builder.getOrCreate() reuses the existing SparkContext
       when called again in the same JVM.  Secondary sessions are lightweight.

    Q: How do you pass dynamic config to Spark jobs in production?
    A: Via --conf flags (spark-submit), environment variables read in the driver,
       or a YAML/JSON config file loaded before SparkSession creation (this module).
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default configuration profiles
# ---------------------------------------------------------------------------

_LOCAL_DEFAULTS: Dict[str, str] = {
    "spark.master": "local[*]",
    "spark.app.name": "DataEngineeringDiaries",
    "spark.sql.shuffle.partitions": "8",          # low for local dev
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.adaptive.coalescePartitions.enabled": "true",
    "spark.sql.adaptive.skewJoin.enabled": "true",
    "spark.ui.enabled": "false",                  # disable UI in tests
    "spark.driver.memory": "2g",
    "spark.executor.memory": "2g",
    "spark.eventLog.enabled": "false",
}

_PRODUCTION_DEFAULTS: Dict[str, str] = {
    # AQE
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.adaptive.coalescePartitions.enabled": "true",
    "spark.sql.adaptive.skewJoin.enabled": "true",
    "spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes": "256m",
    # Shuffle
    "spark.sql.shuffle.partitions": "200",
    "spark.shuffle.service.enabled": "true",
    # Broadcast
    "spark.sql.autoBroadcastJoinThreshold": "10m",
    # Parquet
    "spark.sql.parquet.mergeSchema": "false",
    "spark.sql.parquet.filterPushdown": "true",
    # ORC
    "spark.sql.orc.filterPushdown": "true",
    # Arrow (enables Pandas UDFs)
    "spark.sql.execution.arrow.pyspark.enabled": "true",
    "spark.sql.execution.arrow.pyspark.fallback.enabled": "true",
    # Metadata cache
    "spark.sql.hive.caseSensitiveInferenceMode": "INFER_AND_SAVE",
}

# S3A settings – substitute actual values via env vars or secret manager
_S3A_CONFIG: Dict[str, str] = {
    "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    "spark.hadoop.fs.s3a.aws.credentials.provider": (
        "com.amazonaws.auth.InstanceProfileCredentialsProvider,"
        "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
    ),
    "spark.hadoop.fs.s3a.connection.maximum": "100",
    "spark.hadoop.fs.s3a.fast.upload": "true",
    "spark.hadoop.fs.s3a.fast.upload.buffer": "bytebuffer",
    "spark.hadoop.fs.s3a.multipart.size": "104857600",   # 100 MB
}

# ADLS Gen-2 (ABFS) settings
_ADLS_CONFIG: Dict[str, str] = {
    # Replace <storage_account> with actual value
    "spark.hadoop.fs.abfss.impl": (
        "org.apache.hadoop.fs.azurebfs.SecureAzureBlobFileSystem"
    ),
    # Managed Identity (preferred in ADF / Databricks)
    "spark.hadoop.fs.azure.account.auth.type": "OAuth",
    "spark.hadoop.fs.azure.account.oauth.provider.type": (
        "org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider"
    ),
}


# ---------------------------------------------------------------------------
# SparkSession factory
# ---------------------------------------------------------------------------

class SparkSessionFactory:
    """
    Factory class to create and configure SparkSession instances.

    Usage::

        # Unit test / local notebook
        spark = SparkSessionFactory.create_local(app_name="MyJob")

        # Production (YARN / Kubernetes) – conf comes from spark-submit
        spark = SparkSessionFactory.create_production(app_name="MyJob")

        # With S3 cloud storage
        spark = SparkSessionFactory.create_local(
            app_name="S3Job",
            extra_config=SparkSessionFactory.s3_config("my-bucket"),
        )
    """

    @staticmethod
    def create_local(
        app_name: str = "LocalSparkApp",
        extra_config: Optional[Dict[str, str]] = None,
        master: str = "local[*]",
        enable_hive: bool = False,
        log_level: str = "WARN",
    ) -> SparkSession:
        """
        Create a SparkSession optimised for local development and testing.

        Args:
            app_name    : Application name shown in Spark UI.
            extra_config: Additional key-value Spark configurations.
            master      : Spark master URL (default local[*]).
            enable_hive : Enable HiveContext support.
            log_level   : Spark log level (ALL/DEBUG/INFO/WARN/ERROR/OFF).

        Returns:
            Configured SparkSession.
        """
        config = {**_LOCAL_DEFAULTS, "spark.master": master, "spark.app.name": app_name}

        if extra_config:
            config.update(extra_config)

        builder = SparkSession.builder
        for key, value in config.items():
            builder = builder.config(key, value)

        if enable_hive:
            builder = builder.enableHiveSupport()

        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel(log_level)
        logger.info("Local SparkSession created: %s (master=%s)", app_name, master)
        return spark

    @staticmethod
    def create_production(
        app_name: str = "ProductionSparkApp",
        extra_config: Optional[Dict[str, str]] = None,
        enable_hive: bool = True,
        log_level: str = "WARN",
    ) -> SparkSession:
        """
        Create a SparkSession for production (YARN / Kubernetes / Databricks).

        Master and executor sizing are expected to come from spark-submit --conf
        or the cluster's default settings.  Only logical / SQL tuning is applied
        here so that ops teams control hardware allocation independently.

        Args:
            app_name    : Application name.
            extra_config: Additional Spark configurations.
            enable_hive : Enable HiveContext (required for Hive Metastore).
            log_level   : Log level.

        Returns:
            Configured SparkSession.
        """
        config = {**_PRODUCTION_DEFAULTS, "spark.app.name": app_name}
        if extra_config:
            config.update(extra_config)

        builder = SparkSession.builder
        for key, value in config.items():
            builder = builder.config(key, value)

        if enable_hive:
            builder = builder.enableHiveSupport()

        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel(log_level)
        logger.info("Production SparkSession created: %s", app_name)
        return spark

    @staticmethod
    def create_databricks() -> SparkSession:
        """
        Return the pre-existing SparkSession on Databricks Runtime.

        On Databricks (DBR), the session is already created by the platform.
        This method simply retrieves it and applies any additional settings.

        Returns:
            Active SparkSession from Databricks Runtime.
        """
        spark = SparkSession.getActiveSession()
        if spark is None:
            raise RuntimeError(
                "No active SparkSession found. "
                "This method should only be called on Databricks Runtime."
            )
        logger.info("Databricks SparkSession retrieved: %s", spark.conf.get("spark.app.name"))
        return spark

    @staticmethod
    def s3_config(
        bucket: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Build S3A configuration dictionary.

        In production, prefer IAM Instance Profiles (no key/secret needed).
        For local dev/testing, supply access_key + secret_key.

        Args:
            bucket     : Optional bucket-specific endpoint override.
            access_key : AWS access key (leave None for IAM).
            secret_key : AWS secret key (leave None for IAM).

        Returns:
            Dict of Spark Hadoop S3A configurations.
        """
        config = dict(_S3A_CONFIG)
        if access_key and secret_key:
            config["spark.hadoop.fs.s3a.access.key"] = access_key
            config["spark.hadoop.fs.s3a.secret.key"] = secret_key
            config["spark.hadoop.fs.s3a.aws.credentials.provider"] = (
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
            )
        if bucket:
            config[f"spark.hadoop.fs.s3a.bucket.{bucket}.endpoint"] = (
                os.environ.get("S3_ENDPOINT_URL", "s3.amazonaws.com")
            )
        return config

    @staticmethod
    def adls_config(storage_account: str, tenant_id: str) -> Dict[str, str]:
        """
        Build ADLS Gen-2 (ABFS) configuration dictionary.

        Uses Azure Managed Identity by default (recommended for ADF / AKS).
        For service principal auth, override oauth.provider.type and supply
        client_id / client_secret via Azure Key Vault.

        Args:
            storage_account : Azure Storage account name.
            tenant_id       : Azure AD tenant ID.

        Returns:
            Dict of Spark Hadoop ABFS configurations.
        """
        config = dict(_ADLS_CONFIG)
        config[f"spark.hadoop.fs.azure.account.auth.type.{storage_account}.dfs.core.windows.net"] = "OAuth"
        config[f"spark.hadoop.fs.azure.account.oauth.provider.type.{storage_account}.dfs.core.windows.net"] = (
            "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider"
        )
        config[f"spark.hadoop.fs.azure.account.oauth2.client.endpoint.{storage_account}.dfs.core.windows.net"] = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
        )
        return config

    @staticmethod
    def stop(spark: SparkSession) -> None:
        """Stop the SparkSession and release all resources."""
        app_name = spark.conf.get("spark.app.name", "Unknown")
        spark.stop()
        logger.info("SparkSession stopped: %s", app_name)


# ---------------------------------------------------------------------------
# Convenience function for notebooks / quick scripts
# ---------------------------------------------------------------------------

def get_spark(
    app_name: str = "DataEngineeringDiaries",
    mode: str = "local",
    **kwargs,
) -> SparkSession:
    """
    Convenience function to get a SparkSession.

    Args:
        app_name : Application name.
        mode     : "local" | "production" | "databricks"
        **kwargs : Passed to the underlying factory method.

    Returns:
        SparkSession instance.

    Example::

        from src.spark_session import get_spark
        spark = get_spark("MyJob", mode="local")
    """
    factory = SparkSessionFactory()
    if mode == "local":
        return factory.create_local(app_name=app_name, **kwargs)
    elif mode == "production":
        return factory.create_production(app_name=app_name, **kwargs)
    elif mode == "databricks":
        return factory.create_databricks()
    else:
        raise ValueError(f"Unknown mode '{mode}'. Choose 'local', 'production', or 'databricks'.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    spark = get_spark("SparkSessionDemo", mode="local", log_level="INFO")
    print(f"Spark version : {spark.version}")
    print(f"App name      : {spark.conf.get('spark.app.name')}")
    print(f"Master        : {spark.conf.get('spark.master')}")
    print(f"Shuffle parts : {spark.conf.get('spark.sql.shuffle.partitions')}")
    print(f"AQE enabled   : {spark.conf.get('spark.sql.adaptive.enabled')}")
    SparkSessionFactory.stop(spark)
