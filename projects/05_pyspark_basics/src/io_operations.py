"""
io_operations.py
================
Production IO operations for PySpark: Reading and Writing CSV, JSON, Parquet, and Delta formats.

Business Use Case:
    Ingest data from raw cloud storage landing zones (S3 / ADLS), apply partition strategies,
    compress data using Snappy/ZSTD, and persist outputs to gold/silver tables in Parquet/Delta formats.

Format Comparison:
    - CSV: Human readable, row-oriented, slow to query, no native compression/metadata.
    - JSON: Semi-structured, row-oriented, supports nested structures, schema inference overhead.
    - Parquet: Columnar binary format, highly compressed (Snappy/GSTD), dictionary encoded, predicate pushdown.
    - Delta Lake: ACID transactional layer on Parquet with time travel, schema enforcement, and MERGE capability.

Interview Questions:
    Q: What is predicate pushdown in Parquet/Delta?
    A: Predicate pushdown pushes WHERE filters down to the file reader layer.
       Spark reads file footer metadata (min/max row group values) to skip entire
       row groups without scanning their actual data bytes.

    Q: Why should you avoid partitionBy on high-cardinality columns (e.g. timestamp or UUID)?
    A: High cardinality causes the "small files problem" — millions of tiny folders/files created
       on object storage, degrading Metastore metadata queries and causing massive overhead.

    Q: How do you handle schema evolution when writing Parquet/Delta files?
    A: For Delta Lake, set `.option("mergeSchema", "true")`. Parquet requires reading with
       `spark.sql.parquet.mergeSchema=true`.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType

logger = logging.getLogger(__name__)


class PySparkIO:
    """
    Production I/O manager for PySpark reading and writing operations.
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark

    def read_csv(
        self,
        file_path: str,
        schema: Optional[StructType] = None,
        delimiter: str = ",",
        header: bool = True,
        corrupt_record_col: str = "_corrupt_record",
    ) -> DataFrame:
        """
        Read CSV with permissive error mode and optional explicit schema.

        Args:
            file_path: Input file or directory path.
            schema: StructType schema.
            delimiter: Column delimiter character.
            header: First line as header.
            corrupt_record_col: Target column for malformed records.

        Returns:
            DataFrame.
        """
        reader = (
            self.spark.read
            .option("header", str(header).lower())
            .option("delimiter", delimiter)
            .option("mode", "PERMISSIVE")
            .option("columnNameOfCorruptRecord", corrupt_record_col)
        )
        if schema:
            reader = reader.schema(schema)
        else:
            reader = reader.option("inferSchema", "true")

        logger.info("Reading CSV from: %s", file_path)
        return reader.csv(file_path)

    def read_json(
        self,
        file_path: str,
        schema: Optional[StructType] = None,
        multiline: bool = True,
    ) -> DataFrame:
        """
        Read JSON or JSONL files into DataFrame.

        Args:
            file_path: Path to JSON source.
            schema: Optional StructType schema.
            multiline: True for multi-line JSON arrays, False for line-delimited JSON.

        Returns:
            DataFrame.
        """
        reader = self.spark.read.option("multiline", str(multiline).lower())
        if schema:
            reader = reader.schema(schema)

        logger.info("Reading JSON from: %s", file_path)
        return reader.json(file_path)

    def read_parquet(self, file_path: str) -> DataFrame:
        """
        Read Parquet files from path.

        Args:
            file_path: Parquet file path or directory.

        Returns:
            DataFrame.
        """
        logger.info("Reading Parquet from: %s", file_path)
        return self.spark.read.parquet(file_path)

    def write_parquet(
        self,
        df: DataFrame,
        output_path: str,
        mode: str = "overwrite",
        partition_cols: Optional[List[str]] = None,
        compression: str = "snappy",
    ) -> None:
        """
        Write DataFrame in Parquet format with Snappy compression and partitioning.

        Args:
            df: DataFrame to write.
            output_path: Destination directory path.
            mode: 'overwrite', 'append', 'ignore', 'errorifexists'.
            partition_cols: List of column names to partition by.
            compression: Compression codec ('snappy', 'gzip', 'zstd', 'none').
        """
        writer = df.write.mode(mode).option("compression", compression)
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)

        logger.info("Writing Parquet to '%s' (mode=%s, compression=%s)", output_path, mode, compression)
        writer.parquet(output_path)

    def write_delta(
        self,
        df: DataFrame,
        output_path: str,
        mode: str = "overwrite",
        partition_cols: Optional[List[str]] = None,
        merge_schema: bool = False,
    ) -> None:
        """
        Write DataFrame in Delta Lake format.

        Args:
            df: Input DataFrame.
            output_path: Output table path.
            mode: Write mode.
            partition_cols: Partitioning columns.
            merge_schema: Enable schema evolution.
        """
        writer = df.write.format("delta").mode(mode)
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
        if merge_schema:
            writer = writer.option("mergeSchema", "true")

        logger.info("Writing Delta table to '%s' (mode=%s)", output_path, mode)
        writer.save(output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("IODemo")
    io = PySparkIO(spark)
    sales = create_sample_sales(spark)

    target_dir = "sample-data/output_test_parquet"
    io.write_parquet(sales, target_dir, mode="overwrite", partition_cols=["category"])
    df_reloaded = io.read_parquet(target_dir)
    print(f"Reloaded Parquet count: {df_reloaded.count()}")

    spark.stop()
