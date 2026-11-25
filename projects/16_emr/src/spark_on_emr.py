"""
Production PySpark ETL script designed to execute on Amazon EMR or locally.
Reads transaction data, performs analytics aggregations, and writes partition-optimized Parquet to S3.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import sys
import logging
from datetime import datetime
from typing import Optional
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, year, month, dayofmonth, sum as spark_sum, count, lit, when

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SparkOnEMR")


def create_spark_session(app_name: str = "EMR-Spark-ETL-Job", is_local: bool = False) -> SparkSession:
    """
    Creates and configures a SparkSession optimized for EMR S3 read/writes.
    """
    logger.info("Initializing Spark Session. Local Mode: %s", is_local)
    
    builder = SparkSession.builder.appName(app_name)
    
    if is_local:
        # Local configuration for testing
        builder = (
            builder.master("local[*]")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.default.parallelism", "4")
        )
    else:
        # EMR Production configurations
        builder = (
            builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.dynamicAllocation.enabled", "true")
            # Optimizing for S3 writes and consistent listings (using EMRFS/S3A)
            .config("spark.hadoop.fs.s3.impl", "com.amazon.ws.emr.hadoop.fs.EmrFileSystem")
            .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        )
        
    return builder.getOrCreate()


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> None:
    """
    Executes the Spark ETL pipeline:
      1. Reads CSV transaction data.
      2. Cleans schema and parses dates.
      3. Filters invalid transactions.
      4. Calculates business metrics.
      5. Writes partition-optimized Parquet to output path.
    """
    logger.info("Starting ETL process...")
    logger.info("Reading input from: %s", input_path)
    
    # Read raw CSV transaction data
    df_raw = spark.read.option("header", "true").option("inferSchema", "true").csv(input_path)
    
    logger.info("Raw schema:")
    df_raw.printSchema()
    
    # 1. Clean schema and cast timestamps
    df_cleaned = df_raw.withColumn(
        "transaction_timestamp", to_timestamp(col("transaction_date"), "yyyy-MM-dd HH:mm:ss")
    ).withColumn(
        "amount", col("amount").cast("double")
    )
    
    # 2. Filter out FAILED transactions (business logic)
    df_filtered = df_cleaned.filter(col("status") != "FAILED")
    
    # 3. Add calendar lookup dimensions for partitioning
    df_enriched = df_filtered.withColumn(
        "year", year(col("transaction_timestamp"))
    ).withColumn(
        "month", month(col("transaction_timestamp"))
    )
    
    # 4. Perform analytical aggregations: Total transaction amount and count by customer category and country
    logger.info("Computing aggregation metrics...")
    df_summary = df_enriched.groupBy("country", "category", "year", "month").agg(
        spark_sum("amount").alias("total_sales_amount"),
        count("transaction_id").alias("transaction_count")
    )
    
    # Add extraction timestamp
    df_summary = df_summary.withColumn("processed_at", lit(datetime.utcnow().isoformat()))
    
    logger.info("Aggregate Summary Example (first 5 records):")
    df_summary.show(5, truncate=False)
    
    # 5. Write the optimized, partitioned Parquet output
    logger.info("Writing optimized Parquet to: %s", output_path)
    
    # Coalesce to avoid small files problem (production partition tuning)
    # We partition by year, month, and country
    (
        df_summary.repartition(col("year"), col("month"), col("country"))
        .write
        .mode("overwrite")
        .partitionBy("year", "month", "country")
        .parquet(output_path)
    )
    
    logger.info("ETL job completed successfully!")


def main() -> None:
    """
    Entry point for the EMR step execution.
    Expects two CLI arguments: <input_path> <output_path>
    """
    if len(sys.argv) < 3:
        logger.error("Missing command line arguments. Usage: spark_on_emr.py <input_path> <output_path>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # Check if we should use local config
    is_local_run = input_path.startswith("file://") or "/" in input_path and not input_path.startswith("s3://")
    
    spark = create_spark_session(is_local=is_local_run)
    try:
        run_etl(spark, input_path, output_path)
    except Exception as e:
        logger.error("Exception occurred during execution of ETL: %s", str(e), exc_info=True)
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
