import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils
from src.silver.data_quality_checks import DataQualityChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SilverCustomersProcessor:
    """Processes Bronze customer records into clean, validated Silver tables."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.bronze_customers_path = Path(self.storage_cfg.get("bronze_path")) / "customers"
        self.silver_customers_path = Path(self.storage_cfg.get("silver_path")) / "customers"
        self.spark = bronze_utils.get_spark_session(self.config)
        self.dq = DataQualityChecker(self.config)

    def process(self):
        logger.info("Starting Silver layer processing for customers...")

        if self.spark:
            df_bronze = self.spark.read.format("delta").load(str(self.bronze_customers_path))
            
            from pyspark.sql.functions import col, trim, to_timestamp, lower
            df_clean = df_bronze.select(
                trim(col("customer_id")).alias("customer_id"),
                trim(col("first_name")).alias("first_name"),
                trim(col("last_name")).alias("last_name"),
                lower(trim(col("email"))).alias("email"),
                trim(col("phone")).alias("phone"),
                to_timestamp(col("created_at")).alias("created_at"),
                to_timestamp(col("updated_at")).alias("updated_at"),
                trim(col("country")).alias("country"),
                trim(col("segment")).alias("segment"),
                col("_ingested_at"),
                col("_source_file")
            ).dropDuplicates(["customer_id"])

            # Run DQ checks
            logger.info("Executing Data Quality checks on customers...")
            null_res = self.dq.run_null_check(df_clean, ["customer_id", "email", "country"])
            pk_res = self.dq.run_uniqueness_check(df_clean, ["customer_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, PK: {pk_res['pass']}")

            # Save
            df_clean.write.format("delta").mode("overwrite").save(str(self.silver_customers_path))
            logger.info(f"Customers saved to Silver Delta: {self.silver_customers_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_bronze = bronze_utils.load_fallback_df(self.bronze_customers_path)
            if df_bronze.empty:
                logger.error("No bronze data found for customers fallback processing.")
                return
            
            df_clean = df_bronze.copy()
            df_clean["customer_id"] = df_clean["customer_id"].astype(str).str.strip()
            df_clean["first_name"] = df_clean["first_name"].astype(str).str.strip()
            df_clean["last_name"] = df_clean["last_name"].astype(str).str.strip()
            df_clean["email"] = df_clean["email"].astype(str).str.strip().str.lower()
            df_clean["phone"] = df_clean["phone"].astype(str).str.strip()
            df_clean["created_at"] = pd.to_datetime(df_clean["created_at"])
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"])
            df_clean["country"] = df_clean["country"].astype(str).str.strip()
            df_clean["segment"] = df_clean["segment"].astype(str).str.strip()
            
            df_clean = df_clean.drop_duplicates(subset=["customer_id"])

            # Run DQ checks
            logger.info("Executing Data Quality checks on customers (Pandas fallback)...")
            null_res = self.dq.run_null_check(df_clean, ["customer_id", "email", "country"])
            pk_res = self.dq.run_uniqueness_check(df_clean, ["customer_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, PK: {pk_res['pass']}")

            bronze_utils.save_fallback_df(df_clean, self.silver_customers_path)

        logger.info("Silver customers processing completed successfully.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = SilverCustomersProcessor(cfg)
    processor.process()
