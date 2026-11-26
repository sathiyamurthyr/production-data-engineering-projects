import os
import logging
from pathlib import Path
from datetime import datetime
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Try importing pyspark and delta
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import current_timestamp, lit
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False
    logger.warning("pyspark is not installed in the environment. Running in mock Spark mode.")

def get_spark_session(config: PipelineConfig) -> "SparkSession":
    """Configures and returns a Spark Session with Delta Lake support."""
    if not PYSPARK_AVAILABLE:
        logger.info("Mocking Spark Session for local environment...")
        return None

    spark_cfg = config.spark_config
    app_name = spark_cfg.get("app_name", "DataMartCapstone")
    master = spark_cfg.get("master", "local[*]")
    
    builder = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.sql.extensions", spark_cfg.get("extensions", "io.delta.sql.DeltaSparkSessionExtension")) \
        .config("spark.sql.catalog.spark_catalog", spark_cfg.get("catalog", {}).get("spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")) \
        .config("spark.sql.shuffle.partitions", str(spark_cfg.get("shuffle_partitions", 4)))

    spark = builder.getOrCreate()
    logger.info("Spark Session successfully initialized with Delta Lake support.")
    return spark

def add_ingestion_metadata(df: "DataFrame", source_file: str) -> "DataFrame":
    """Appends standard data lineage audit columns to a DataFrame."""
    if not PYSPARK_AVAILABLE or df is None:
        return df
    return df.withColumn("_ingested_at", current_timestamp()) \
             .withColumn("_source_file", lit(source_file))

def write_to_delta(df: "DataFrame", target_path: str, mode: str = "overwrite"):
    """Writes a DataFrame to Delta format at the specified target path."""
    if not PYSPARK_AVAILABLE or df is None:
        logger.info(f"Mock Writing DataFrame to {target_path} (mode={mode})")
        return
    logger.info(f"Writing dataset to Delta destination: {target_path}")
    df.write.format("delta").mode(mode).save(target_path)
    logger.info("Delta write completed successfully.")

# --- Local Fallback Helpers (for executing without Spark or PyArrow) ---

def save_fallback_df(df, target_path: Path, filename: str = "part-0"):
    """Saves a Pandas DataFrame to Parquet if possible, else falls back to CSV."""
    target_path.mkdir(parents=True, exist_ok=True)
    try:
        import pyarrow
        target_file = target_path / f"{filename}.parquet"
        df.to_parquet(target_file, index=False)
        logger.info(f"Saved fallback Parquet to {target_file}")
    except ImportError:
        target_file = target_path / f"{filename}.csv"
        df.to_csv(target_file, index=False)
        logger.info(f"pyarrow not found. Saved fallback CSV to {target_file}")

def load_fallback_df(target_path: Path):
    """Loads a dataset from target path checking for Parquet first, then CSV."""
    import pandas as pd
    if not target_path.exists():
        logger.warning(f"Target path does not exist: {target_path}")
        return pd.DataFrame()
    
    # Check for parquet
    parquet_files = list(target_path.glob("**/*.parquet"))
    if parquet_files:
        try:
            return pd.concat([pd.read_parquet(f) for f in parquet_files], ignore_index=True)
        except Exception as e:
            logger.warning(f"Failed to read Parquet files at {target_path}: {e}")
            
    # Check for CSV
    csv_files = list(target_path.glob("**/*.csv"))
    if csv_files:
        try:
            return pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
        except Exception as e:
            logger.error(f"Failed to read CSV files at {target_path}: {e}")
            
    return pd.DataFrame()
