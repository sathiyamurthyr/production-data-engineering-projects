"""
Hive Metastore and AWS Glue Data Catalog Integration on EMR.
Demonstrates setting up Spark with Hive Metastore support, orchestrating Hive DDL/DML tables,
and managing partitions dynamically in AWS Glue Data Catalog.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
from typing import Dict, Any, Optional
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HiveOnEMR")


class HiveCatalogManager:
    """
    Manages Spark SQL operations on EMR integrated with Hive Metastore / AWS Glue Data Catalog.
    """

    @staticmethod
    def create_spark_with_hive(app_name: str = "EMR-Hive-Metastore-Job", use_glue_catalog: bool = True) -> SparkSession:
        """
        Creates a SparkSession configured to use the external Hive Metastore (AWS Glue Catalog by default on EMR).
        """
        logger.info("Initializing SparkSession with Hive Support. Using Glue Catalog: %s", use_glue_catalog)
        
        builder = SparkSession.builder.appName(app_name).enableHiveSupport()
        
        if use_glue_catalog:
            # EMR configurations to bind Spark SQL metastore to AWS Glue Data Catalog
            builder = (
                builder.config("hive.metastore.client.factory.class", "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory")
                .config("spark.sql.hive.metastore.sharedPrefixes", "com.amazonaws.services.securitytoken,com.amazonaws.services.glue,com.amazonaws.glue")
            )
        else:
            # Traditional self-hosted Hive Metastore configurations (e.g. RDS MySQL/PostgreSQL)
            # Typically set via hive-site.xml, but can be set programmatically:
            # builder = builder.config("hive.metastore.uris", "thrift://metastore-host:9083")
            pass

        # Enable dynamic partitioning configuration
        builder = (
            builder.config("spark.sql.sources.partitionOverwriteMode", "dynamic")
            .config("hive.exec.dynamic.partition", "true")
            .config("hive.exec.dynamic.partition.mode", "nonstrict")
        )
        
        return builder.getOrCreate()

    @staticmethod
    def create_external_table_hql(
        database_name: str,
        table_name: str,
        s3_location: str,
        partition_schema: str = "year INT, month INT, country STRING",
        schema_definition: str = "transaction_id STRING, customer_id STRING, amount DOUBLE, transaction_date STRING, category STRING, payment_method STRING, status STRING"
    ) -> str:
        """
        Generates Hive Query Language (HQL) to construct an external Parquet table.
        """
        if not s3_location.startswith("s3://") and not s3_location.startswith("file://"):
            raise ValueError("Table location must be a valid S3 URI")

        # Create Database and Table query
        hql = f"""
        CREATE DATABASE IF NOT EXISTS {database_name};
        
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {schema_definition}
        )
        PARTITIONED BY (
            {partition_schema}
        )
        STORED AS PARQUET
        LOCATION '{s3_location}';
        """
        return hql

    def setup_catalog_table(self, spark: SparkSession, database_name: str, table_name: str, s3_location: str) -> None:
        """
        Executes Hive DDL to register the external table and sync metadata.
        """
        logger.info("Setting up Hive table %s.%s at location %s", database_name, table_name, s3_location)
        
        # 1. Create database and table in the catalog
        hql = self.create_external_table_hql(database_name, table_name, s3_location)
        logger.info("Executing HQL:\n%s", hql)
        
        # Run statements
        statements = [stmt.strip() for stmt in hql.strip().split(";") if stmt.strip()]
        for stmt in statements:
            spark.sql(stmt)

        # 2. Recover partitions to ensure Catalog tracks existing files in S3
        # In AWS Glue Catalog / Hive Metastore, MSCK REPAIR TABLE registers new directories
        repair_hql = f"MSCK REPAIR TABLE {database_name}.{table_name}"
        logger.info("Recovering partitions using: %s", repair_hql)
        spark.sql(repair_hql)
        
        logger.info("Catalog sync completed successfully.")

    def write_to_hive_table(self, spark: SparkSession, df: Any, database_name: str, table_name: str) -> None:
        """
        Writes PySpark DataFrame directly to a Hive table using Partition Overwrite Mode.
        """
        logger.info("Writing DataFrame to Hive Managed/External table: %s.%s", database_name, table_name)
        
        # Check if table exists
        table_exists = spark.catalog.tableExists(f"{database_name}.{table_name}")
        
        if not table_exists:
            logger.info("Table does not exist. Saving as new Hive table...")
            # Automatically registers in Glue Catalog
            df.write.mode("overwrite").format("parquet").saveAsTable(f"{database_name}.{table_name}")
        else:
            logger.info("Table exists. Writing using dynamic partitioning insertions...")
            # Insert into existing table structure
            df.write.mode("overwrite").insertInto(f"{database_name}.{table_name}")
            
        logger.info("Successfully written data to Hive table.")
        
    def query_hive_table(self, spark: SparkSession, database_name: str, table_name: str, limit: int = 10) -> Any:
        """
        Queries the Glue Catalog/Hive table using Spark SQL.
        """
        query = f"SELECT * FROM {database_name}.{table_name} LIMIT {limit}"
        logger.info("Running query: %s", query)
        df = spark.sql(query)
        df.show()
        return df
