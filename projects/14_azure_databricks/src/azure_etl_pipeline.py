"""
Azure End-to-End ETL Pipeline (ADLS Gen2 -> Databricks Delta Lake -> Azure Synapse)
===================================================================================
Production-grade Azure Databricks ETL pipeline processing multi-stage data pipelines
from landing zones on ADLS Gen2 through Medallion architecture (Bronze/Silver/Gold)
to Azure Synapse Analytics dedicated SQL pools.

Business Use Case:
    Enterprise data platform processing high-volume transactional records (e.g. e-commerce orders).
    Raw files arrive continuously in ADLS Gen2. The pipeline enforces schema validation,
    data quality rules, deduplication, incremental merging (SCD Type 1/2), aggregations,
    and publishes reporting-ready data into Azure Synapse Analytics for BI consumption.

Architecture:
    ADLS Gen2 (abfss://raw@...)
        │ (Auto Loader / Spark Read)
        ▼
    Databricks Bronze Layer (Delta - Raw with Ingestion Metadata)
        │ (Data Cleansing, Validation, Schema Enforcement)
        ▼
    Databricks Silver Layer (Delta - Cleansed & Deduplicated)
        │ (Business Aggregations, KPIs)
        ▼
    Databricks Gold Layer (Delta - Aggregations & Star Schema)
        │ (Synapse Spark Connector / PolyBase / COPY INTO)
        ▼
    Azure Synapse Dedicated SQL Pool (DW Reporting Tables)

Performance Notes:
    - Bronze to Silver: Leverage Delta Auto Loader (cloudFiles) for streaming ingestion.
    - Silver: Optimize with liquid clustering or Z-ORDER BY (customer_id, event_date).
    - Gold to Synapse: Use Azure Synapse Spark connector with Azure Storage staging location
      and Azure AD Managed Identity or Service Principal for PolyBase/COPY INTO parallel loading.

Common Mistakes:
    - Using JDBC single-threaded driver instead of Azure Synapse Spark connector for large datasets.
    - Writing non-idempotent pipelines that fail on re-run (always use MERGE INTO or partition overwrites).
    - Hardcoding Synapse credentials in notebooks instead of retrieving from Azure Key Vault scopes.
    - Omitting temporary Azure Blob Storage credentials required for Synapse bulk staging.

Interview Questions:
    Q: How do you push data from Databricks to Azure Synapse efficiently?
    A: Use the Azure Synapse Spark Connector (`com.databricks.spark.sqldw`). It stage-loads data
       as Parquet files into ADLS Gen2/Blob storage and uses PolyBase or high-speed `COPY INTO`
       commands to load into Synapse parallel nodes in bulk, avoiding single-threaded JDBC bottlenecks.

    Q: What is the Medallion Architecture and why is it used in Azure Databricks?
    A: It organizes data into three distinct layers: Bronze (raw, append-only), Silver (cleaned,
       conformed, deduplicated), and Gold (aggregated, business metrics). This structure ensures
       data quality isolation, traceably audited transformations, and optimal performance for different access patterns.

    Q: How do you handle schema evolution in Delta Lake during Bronze ingestion?
    A: Enable schema evolution using `.option("mergeSchema", "true")` or Auto Loader's
       `schemaEvolutionMode` ("addNewColumns", "rescue"). Rescued data can be captured in a
       `_rescued_data` column without breaking down stream jobs.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType,
        IntegerType, TimestampType, DateType
    )
    from delta.tables import DeltaTable
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AzureETLPipeline")


@dataclass
class AzureETLPipelineConfig:
    """Configuration container for Azure ETL Pipeline execution."""
    storage_account_name: str = "stmedallionprod"
    raw_container: str = "raw"
    bronze_container: str = "bronze"
    silver_container: str = "silver"
    gold_container: str = "gold"
    synapse_server: str = "synw-prod-dw.sql.azuresynapse.net"
    synapse_database: str = "sqldw_analytics"
    synapse_staging_container: str = "synapse-staging"
    secret_scope: str = "akv-prod-scope"
    key_vault_secret_synapse_dw: str = "synapse-sql-auth"
    checkpoint_location_base: str = "/mnt/checkpoints"

    def get_abfss_path(self, container: str, path: str = "") -> str:
        """Construct ABFSS URI for target ADLS Gen2 container and path."""
        clean_path = path.strip("/")
        if clean_path:
            return f"abfss://{container}@{self.storage_account_name}.dfs.core.windows.net/{clean_path}"
        return f"abfss://{container}@{self.storage_account_name}.dfs.core.windows.net"


class AzureETLPipeline:
    """
    End-to-End Enterprise ETL Pipeline on Azure Databricks.
    Processes raw files from ADLS Gen2 through Medallion Delta layers and loads Synapse DW.
    """

    def __init__(self, spark: Optional[Any] = None, config: Optional[AzureETLPipelineConfig] = None):
        self.spark = spark
        self.config = config or AzureETLPipelineConfig()
        self._validate_spark()

    def _validate_spark(self) -> None:
        """Ensure PySpark environment is available or initialized."""
        if self.spark is None and HAS_PYSPARK:
            try:
                self.spark = SparkSession.builder \
                    .appName("AzureETLPipeline") \
                    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
                    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
                    .getOrCreate()
            except Exception as e:
                logger.warning(f"Could not build local SparkSession: {e}")

    def define_bronze_schema(self) -> Any:
        """
        Define strict expected schema for incoming raw order data.
        Returns StructType schema.
        """
        if not HAS_PYSPARK:
            return None
        return StructType([
            StructField("order_id", StringType(), False),
            StructField("customer_id", StringType(), True),
            StructField("order_timestamp", StringType(), True),
            StructField("product_id", StringType(), True),
            StructField("quantity", IntegerType(), True),
            StructField("unit_price", DoubleType(), True),
            StructField("status", StringType(), True),
            StructField("store_region", StringType(), True),
        ])

    def read_bronze_from_adls(self, source_file_path: Optional[str] = None) -> Any:
        """
        Ingest raw files from ADLS Gen2 into Bronze Delta layer.
        Injects ingestion metadata: file name, ingestion timestamp, and process batch id.
        """
        logger.info("Starting Bronze Ingestion from ADLS Gen2...")
        path = source_file_path or self.config.get_abfss_path(self.config.raw_container, "orders/year=2026/*")
        
        if not HAS_PYSPARK or self.spark is None:
            logger.info(f"Simulating Bronze ingestion read from path: {path}")
            return None

        schema = self.define_bronze_schema()
        
        # Ingest raw files with schema validation and metadata injection
        raw_df = self.spark.read \
            .option("header", "true") \
            .schema(schema) \
            .json(path)
            
        bronze_df = raw_df \
            .withColumn("_ingestion_timestamp", F.current_timestamp()) \
            .withColumn("_source_file", F.input_file_name()) \
            .withColumn("_ingestion_date", F.current_date())

        logger.info("Successfully read Bronze data from ADLS Gen2.")
        return bronze_df

    def write_to_bronze_table(self, bronze_df: Any, target_table: str = "bronze_orders") -> None:
        """
        Write transformed Bronze dataframe to Delta table in ADLS Gen2.
        """
        if bronze_df is None or not HAS_PYSPARK:
            logger.info(f"Simulating write to Bronze table '{target_table}'")
            return

        bronze_path = self.config.get_abfss_path(self.config.bronze_container, target_table)
        logger.info(f"Writing Bronze Delta table to: {bronze_path}")

        bronze_df.write \
            .format("delta") \
            .mode("append") \
            .partitionBy("_ingestion_date") \
            .option("checkpointLocation", f"{self.config.checkpoint_location_base}/bronze_orders") \
            .save(bronze_path)

    def transform_silver(self, bronze_df: Any) -> Any:
        """
        Cleanse, cast, filter invalid records, and deduplicate Bronze data into Silver.
        
        Rules:
        - Cast order_timestamp to TimestampType
        - Calculate order_amount = quantity * unit_price
        - Filter out negative quantities or prices
        - Deduplicate based on order_id keeping newest ingestion timestamp
        """
        logger.info("Transforming Bronze data to Silver tier...")
        if bronze_df is None or not HAS_PYSPARK:
            logger.info("Simulating Silver transformation step.")
            return None

        cleaned_df = bronze_df \
            .filter(F.col("order_id").isNotNull()) \
            .filter(F.col("quantity") > 0) \
            .filter(F.col("unit_price") >= 0.0) \
            .withColumn("order_timestamp", F.to_timestamp(F.col("order_timestamp"))) \
            .withColumn("order_amount", F.round(F.col("quantity") * F.col("unit_price"), 2)) \
            .withColumn("status", F.upper(F.trim(F.col("status")))) \
            .withColumn("store_region", F.upper(F.trim(F.col("store_region")))) \
            .withColumn("processed_timestamp", F.current_timestamp())

        # Window specification for deduplication
        from pyspark.sql.window import Window
        window_spec = Window.partitionBy("order_id").orderBy(F.col("_ingestion_timestamp").desc())
        
        silver_df = cleaned_df \
            .withColumn("row_num", F.row_number().over(window_spec)) \
            .filter(F.col("row_num") == 1) \
            .drop("row_num")

        logger.info("Silver transformation complete.")
        return silver_df

    def merge_to_silver_table(self, silver_df: Any, target_table: str = "silver_orders") -> None:
        """
        Perform idempotent MERGE INTO (SCD Type 1) into Silver Delta table on ADLS Gen2.
        """
        if silver_df is None or not HAS_PYSPARK:
            logger.info(f"Simulating MERGE INTO Silver table '{target_table}'")
            return

        silver_path = self.config.get_abfss_path(self.config.silver_container, target_table)
        logger.info(f"Merging into Silver Delta table at: {silver_path}")

        if not DeltaTable.isDeltaTable(self.spark, silver_path):
            logger.info(f"Creating Silver Delta table for first time at {silver_path}")
            silver_df.write.format("delta").partitionBy("store_region").save(silver_path)
            return

        delta_table = DeltaTable.forPath(self.spark, silver_path)
        delta_table.alias("target").merge(
            silver_df.alias("source"),
            "target.order_id = source.order_id"
        ).whenMatchedUpdate(set={
            "customer_id": "source.customer_id",
            "order_timestamp": "source.order_timestamp",
            "product_id": "source.product_id",
            "quantity": "source.quantity",
            "unit_price": "source.unit_price",
            "order_amount": "source.order_amount",
            "status": "source.status",
            "processed_timestamp": "source.processed_timestamp"
        }).whenNotMatchedInsertAll().execute()

        logger.info("Successfully completed MERGE INTO Silver table.")

    def transform_gold(self, silver_df: Any) -> Any:
        """
        Aggregate Silver data into high-value Gold reporting layer.
        Calculates daily region-level KPI aggregations: total revenue, order count, avg order value.
        """
        logger.info("Aggregating Silver data into Gold tier metrics...")
        if silver_df is None or not HAS_PYSPARK:
            logger.info("Simulating Gold transformation step.")
            return None

        gold_df = silver_df \
            .withColumn("order_date", F.to_date(F.col("order_timestamp"))) \
            .groupBy("order_date", "store_region") \
            .agg(
                F.count("order_id").alias("total_orders"),
                F.sum("quantity").alias("total_items_sold"),
                F.round(F.sum("order_amount"), 2).alias("total_revenue"),
                F.round(F.avg("order_amount"), 2).alias("avg_order_value"),
                F.max("processed_timestamp").alias("gold_updated_at")
            )

        logger.info("Gold aggregation metrics created successfully.")
        return gold_df

    def export_to_synapse(
        self,
        gold_df: Any,
        target_synapse_table: str = "dbo.FactDailyRegionSales",
        dbutils: Optional[Any] = None
    ) -> bool:
        """
        Export Gold layer data into Azure Synapse Dedicated SQL Pool using PolyBase/COPY INTO connector.
        
        Secret Scope Retrieval:
        Credentials retrieved securely from Azure Key Vault backed secret scope.
        """
        logger.info(f"Preparing to export Gold metrics to Azure Synapse table: {target_synapse_table}")
        
        # Secret scope retrieval logic
        if dbutils is not None:
            synapse_pwd = dbutils.secrets.get(scope=self.config.secret_scope, key=self.config.key_vault_secret_synapse_dw)
        else:
            synapse_pwd = "MOCK_SYNAPSE_PASSWORD_FROM_KEY_VAULT"

        jdbc_url = (
            f"jdbc:sqlserver://{self.config.synapse_server}:1433;"
            f"database={self.config.synapse_database};"
            f"encrypt=true;trustServerCertificate=false;"
            f"hostNameInCertificate=*.sql.azuresynapse.net;loginTimeout=30;"
        )

        staging_dir = self.config.get_abfss_path(self.config.synapse_staging_container, "synapse_stage")

        if gold_df is None or not HAS_PYSPARK:
            logger.info(f"Simulated export of Gold data to Synapse table '{target_synapse_table}' via staging '{staging_dir}'.")
            return True

        try:
            logger.info("Executing Synapse Spark Bulk Copy...")
            gold_df.write \
                .format("com.databricks.spark.sqldw") \
                .option("url", jdbc_url) \
                .option("user", "synapse_admin_user") \
                .option("password", synapse_pwd) \
                .option("forwardSparkAzureStorageCredentials", "true") \
                .option("dbTable", target_synapse_table) \
                .option("tempDir", staging_dir) \
                .option("maxStrLength", "4000") \
                .mode("overwrite") \
                .save()

            logger.info(f"Successfully exported data to Azure Synapse: {target_synapse_table}")
            return True
        except Exception as e:
            logger.error(f"Failed to export data to Synapse: {str(e)}")
            return False

    def run_pipeline(self, dbutils: Optional[Any] = None) -> Dict[str, Any]:
        """
        Execute end-to-end Medallion Azure Databricks ETL workflow.
        Returns execution statistics and status dictionary.
        """
        start_time = time.time()
        logger.info("=== Starting Azure Databricks End-to-End ETL Pipeline ===")

        stats = {
            "status": "FAILED",
            "bronze_records": 0,
            "silver_records": 0,
            "gold_records": 0,
            "synapse_exported": False,
            "execution_duration_sec": 0.0
        }

        try:
            # Step 1: Ingest Bronze
            bronze_df = self.read_bronze_from_adls()
            self.write_to_bronze_table(bronze_df)

            # Step 2: Transform & Merge Silver
            silver_df = self.transform_silver(bronze_df)
            self.merge_to_silver_table(silver_df)

            # Step 3: Transform & Agg Gold
            gold_df = self.transform_gold(silver_df)

            # Step 4: Export to Synapse
            synapse_success = self.export_to_synapse(gold_df, dbutils=dbutils)

            stats["status"] = "SUCCESS"
            stats["synapse_exported"] = synapse_success
            if HAS_PYSPARK and bronze_df is not None:
                stats["bronze_records"] = bronze_df.count()
                stats["silver_records"] = silver_df.count()
                stats["gold_records"] = gold_df.count()

        except Exception as e:
            logger.error(f"Pipeline execution encountered unhandled error: {e}", exc_info=True)
            stats["error"] = str(e)

        duration = time.time() - start_time
        stats["execution_duration_sec"] = round(duration, 2)
        logger.info(f"=== ETL Pipeline Complete. Status: {stats['status']} (Took {duration:.2f}s) ===")
        return stats


if __name__ == "__main__":
    pipeline = AzureETLPipeline()
    results = pipeline.run_pipeline()
    print("Execution Output:", results)
