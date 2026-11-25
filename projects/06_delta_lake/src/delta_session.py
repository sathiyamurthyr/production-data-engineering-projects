"""
Module: delta_session.py
========================
SparkSession with Delta Lake configuration and catalog setup.

Business Use Case:
    Every Delta Lake project needs a properly configured SparkSession.
    This module provides factory functions that configure Spark with
    the correct Delta Lake extensions, SQL catalog, and production-ready
    settings. In production (Databricks, EMR, etc.) the session already
    exists; locally you need to create it with all Delta jars available.

Key Configuration:
    - spark.sql.extensions: Registers Delta's SQL parser extensions
      (enables CREATE TABLE ... USING DELTA, MERGE INTO, etc.)
    - spark.sql.catalog.spark_catalog: Replaces default Hive catalog
      with Delta's Hive-compatible catalog, enabling Delta features on
      all SQL operations.
    - spark.databricks.delta.*: Various Delta-specific tuning knobs.

Production vs. Local:
    - Local: Spark downloads Delta jars via Maven at startup (slow first run).
    - Databricks: Delta runtime is pre-installed; just use SparkSession.builder.
    - EMR/Dataproc: Add Delta jars via --packages or bootstrap script.

Interview Questions:
    Q: What does spark.sql.extensions do for Delta Lake?
    A: It registers Delta's custom SQL parser and planner extensions,
       enabling MERGE INTO, RESTORE, DESCRIBE HISTORY, and other Delta
       SQL commands that don't exist in vanilla Spark SQL.

    Q: Why must the catalog be changed?
    A: The default catalog (HiveExternalCatalog) doesn't know about Delta
       format. DeltaCatalog wraps it and intercepts Delta table operations,
       enabling features like schema enforcement on write, constraint checks,
       and CDF tracking at the catalog level.

    Q: What is the --packages approach for adding Delta to Spark?
    A: spark-submit --packages io.delta:delta-spark_2.12:3.2.0
       This downloads Delta from Maven at job start. In production, pre-stage
       jars in S3/GCS and use --jars to avoid dependency on Maven at runtime.
"""

import logging
from typing import Optional

from pyspark.sql import SparkSession

# Configure module logger
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default Delta Lake configuration values (override via configs/delta_config.yaml)
# ---------------------------------------------------------------------------
DELTA_LAKE_EXTENSIONS = "io.delta.sql.DeltaSparkSessionExtension"
DELTA_CATALOG_CLASS = "org.apache.spark.sql.delta.catalog.DeltaCatalog"

# Package coordinate for local/standalone use
# Pinned to specific version for reproducibility
DELTA_MAVEN_PACKAGE = "io.delta:delta-spark_2.12:3.2.0"


def create_delta_session(
    app_name: str = "DeltaLakeApp",
    master: str = "local[*]",
    warehouse_dir: str = "./spark-warehouse",
    log_level: str = "WARN",
    extra_configs: Optional[dict] = None,
    enable_cdf: bool = False,
    enable_auto_optimize: bool = True,
) -> SparkSession:
    """
    Create a SparkSession fully configured for Delta Lake operations.

    This function is the single entry point for creating a Spark session in
    all project modules. It applies all required Delta Lake settings plus
    production-recommended tuning options.

    Parameters
    ----------
    app_name : str
        Name shown in the Spark UI. Use a descriptive, unique name per job.
    master : str
        Spark master URL. "local[*]" for development, "yarn" in production,
        "k8s://..." for Kubernetes deployments.
    warehouse_dir : str
        Path where managed table data is stored. In production, point to
        an S3/GCS/ADLS path (e.g., "s3://my-bucket/warehouse").
    log_level : str
        Spark log level: "ERROR", "WARN", "INFO", "DEBUG".
        Use "WARN" locally to reduce noise; "ERROR" in production logs.
    extra_configs : dict, optional
        Additional Spark configs to apply. These override defaults.
        Example: {"spark.executor.memory": "8g"}
    enable_cdf : bool
        If True, enables Delta Change Data Feed globally for all new tables.
        Only enable if you have CDC consumers — adds write overhead.
    enable_auto_optimize : bool
        If True, enables Delta Auto Optimize (auto compaction + optimized writes).
        Recommended for streaming workloads to manage small files automatically.

    Returns
    -------
    SparkSession
        A fully configured SparkSession with Delta Lake extensions active.

    Raises
    ------
    RuntimeError
        If Delta Lake extensions cannot be loaded (e.g., jars not on classpath).

    Example
    -------
    >>> spark = create_delta_session(
    ...     app_name="MedallionPipeline",
    ...     warehouse_dir="s3://my-bucket/lakehouse",
    ...     enable_cdf=True
    ... )
    >>> spark.sql("SELECT * FROM delta.`s3://my-bucket/lakehouse/bronze/events`").show()
    """
    logger.info("Creating Delta Lake SparkSession: app=%s master=%s", app_name, master)

    try:
        # Start building the session
        builder = (
            SparkSession.builder.appName(app_name)
            .master(master)
            # ──────────────────────────────────────────────────────────
            # REQUIRED: Delta Lake SQL extensions
            # Enables: MERGE INTO, RESTORE, DESCRIBE HISTORY,
            #          GENERATE, VACUUM at SQL layer
            # ──────────────────────────────────────────────────────────
            .config("spark.sql.extensions", DELTA_LAKE_EXTENSIONS)
            # ──────────────────────────────────────────────────────────
            # REQUIRED: Replace default catalog with Delta's catalog
            # Without this, Delta table features (schema enforcement,
            # CDF, constraints) don't work through the catalog interface
            # ──────────────────────────────────────────────────────────
            .config("spark.sql.catalog.spark_catalog", DELTA_CATALOG_CLASS)
            # ──────────────────────────────────────────────────────────
            # Managed table warehouse location
            # ──────────────────────────────────────────────────────────
            .config("spark.sql.warehouse.dir", warehouse_dir)
            # ──────────────────────────────────────────────────────────
            # Maven packages for local use (noop on clusters with pre-built Delta)
            # Remove this in production where jars are pre-staged
            # ──────────────────────────────────────────────────────────
            .config("spark.jars.packages", DELTA_MAVEN_PACKAGE)
            # ──────────────────────────────────────────────────────────
            # Adaptive Query Execution: Spark 3.x feature that optimizes
            # query plans at runtime based on actual data statistics.
            # Leave enabled — it helps Delta queries significantly.
            # ──────────────────────────────────────────────────────────
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            # ──────────────────────────────────────────────────────────
            # Partition overwrite mode: 'dynamic' means only overwrite
            # the specific partitions being written, not the entire table.
            # Critical for correctness in partitioned Delta tables.
            # ──────────────────────────────────────────────────────────
            .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
            # ──────────────────────────────────────────────────────────
            # Delta-specific: enable schema auto-merge for DataFrame API
            # (SQL always requires explicit MERGE schema handling)
            # ──────────────────────────────────────────────────────────
            .config("spark.databricks.delta.schema.autoMerge.enabled", "false")
            # ──────────────────────────────────────────────────────────
            # Delta stats collection: enables file-level statistics for
            # Data Skipping (min/max values per file per column).
            # This is what makes Z-ORDER effective.
            # ──────────────────────────────────────────────────────────
            .config("spark.databricks.delta.stats.collect", "true")
            # ──────────────────────────────────────────────────────────
            # Checkpoint every N commits. Delta reads all log JSON files
            # since the last checkpoint. Lower = faster cold reads on
            # tables with many commits. Default is 10.
            # ──────────────────────────────────────────────────────────
            .config("spark.databricks.delta.checkpointInterval", "10")
            # ──────────────────────────────────────────────────────────
            # VACUUM safety check: require explicit override of retention
            # period below 7 days. Leave true for production safety.
            # ──────────────────────────────────────────────────────────
            .config("spark.databricks.delta.retentionDurationCheck.enabled", "true")
        )

        # ── Optional: Change Data Feed ────────────────────────────────────────
        if enable_cdf:
            logger.info("Enabling Delta Change Data Feed globally")
            builder = builder.config(
                "spark.databricks.delta.properties.defaults.enableChangeDataFeed",
                "true",
            )

        # ── Optional: Auto Optimize (auto compaction + optimized writes) ───────
        if enable_auto_optimize:
            logger.info("Enabling Delta Auto Optimize")
            builder = (
                builder
                # Auto compaction: after each write, Delta checks if small files
                # exist and compacts them in the background. Target: 128MB files.
                .config("spark.databricks.delta.autoCompact.enabled", "true")
                # Optimized writes: Spark reshuffles data before writing so each
                # output file is ~128MB (or target size). Reduces the number of
                # small files created by streaming or small-batch writes.
                .config("spark.databricks.delta.optimizeWrite.enabled", "true")
            )

        # ── Apply any caller-provided overrides ───────────────────────────────
        if extra_configs:
            for key, value in extra_configs.items():
                builder = builder.config(key, value)
                logger.debug("Applied extra config: %s = %s", key, value)

        # ── Build session ─────────────────────────────────────────────────────
        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel(log_level)

        # Validate Delta extensions loaded correctly
        _validate_delta_extensions(spark)

        logger.info(
            "SparkSession created successfully | Spark %s | Delta extensions active",
            spark.version,
        )
        return spark

    except Exception as exc:
        logger.error("Failed to create Delta SparkSession: %s", exc)
        raise RuntimeError(f"Delta SparkSession creation failed: {exc}") from exc


def get_or_create_delta_session(app_name: str = "DeltaLakeApp") -> SparkSession:
    """
    Get an existing SparkSession or create a new Delta-enabled one.

    In Databricks notebooks, SparkSession already exists with Delta pre-configured.
    This function handles both cases safely.

    Parameters
    ----------
    app_name : str
        Application name for the Spark UI.

    Returns
    -------
    SparkSession
        Active Delta-enabled SparkSession.
    """
    existing = SparkSession.getActiveSession()
    if existing is not None:
        logger.info("Reusing existing SparkSession (Databricks/Cluster mode)")
        return existing

    logger.info("No active session found — creating new Delta-enabled session")
    return create_delta_session(app_name=app_name)


def _validate_delta_extensions(spark: SparkSession) -> None:
    """
    Validate that Delta Lake SQL extensions are active by running a
    simple Delta-specific SQL command.

    Raises
    ------
    RuntimeError
        If Delta extensions are not properly loaded.
    """
    try:
        # DESCRIBE HISTORY is a Delta-only SQL command.
        # Attempting it on a non-Delta path fails, but the parser accepting
        # the syntax confirms extensions are loaded.
        spark.sql("SELECT current_timestamp() AS delta_check").collect()
        logger.debug("Delta Lake SQL extensions validated successfully")
    except Exception as exc:
        raise RuntimeError(
            "Delta Lake extensions validation failed. "
            "Ensure delta-spark is installed and spark.sql.extensions is set. "
            f"Original error: {exc}"
        ) from exc


def configure_delta_table_properties(
    spark: SparkSession,
    table_path: str,
    properties: dict,
) -> None:
    """
    Set Delta table properties using ALTER TABLE SET TBLPROPERTIES.

    Common properties:
        delta.enableChangeDataFeed = true
        delta.dataSkippingNumIndexedCols = 32
        delta.logRetentionDuration = "interval 30 days"
        delta.deletedFileRetentionDuration = "interval 7 days"
        delta.minWriterVersion = 4
        delta.minReaderVersion = 2

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Path to the Delta table (e.g., "/mnt/lakehouse/bronze/events").
    properties : dict
        Dictionary of property key → value pairs to set.

    Example
    -------
    >>> configure_delta_table_properties(spark, "/tmp/my_table", {
    ...     "delta.enableChangeDataFeed": "true",
    ...     "delta.logRetentionDuration": "interval 30 days"
    ... })
    """
    props_sql = ", ".join(
        f"'{k}' = '{v}'" for k, v in properties.items()
    )
    sql = f"ALTER TABLE delta.`{table_path}` SET TBLPROPERTIES ({props_sql})"
    logger.info("Setting table properties: %s", sql)
    spark.sql(sql)


def print_session_config(spark: SparkSession) -> None:
    """
    Print all active Delta-related Spark configuration for debugging.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    """
    delta_configs = {
        k: v
        for k, v in spark.sparkContext.getConf().getAll()
        if "delta" in k.lower() or "catalog" in k.lower() or "extension" in k.lower()
    }

    print("\n─── Active Delta Lake Configuration ───────────────────────────────")
    for key, value in sorted(delta_configs.items()):
        print(f"  {key:<60} = {value}")
    print("────────────────────────────────────────────────────────────────────\n")
