import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils
from src.silver.data_quality_checks import DataQualityChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SilverOrdersProcessor:
    """Processes Bronze orders data into the cleaned Silver layer."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.bronze_orders_path = Path(self.storage_cfg.get("bronze_path")) / "orders"
        self.silver_orders_path = Path(self.storage_cfg.get("silver_path")) / "orders"
        self.spark = bronze_utils.get_spark_session(self.config)
        self.dq = DataQualityChecker(self.config)

    def process(self):
        logger.info("Starting Silver layer processing for orders...")

        if self.spark:
            df_bronze = self.spark.read.format("delta").load(str(self.bronze_orders_path))
            
            from pyspark.sql.functions import col, to_timestamp, trim
            df_clean = df_bronze.select(
                trim(col("order_id")).alias("order_id"),
                trim(col("customer_id")).alias("customer_id"),
                trim(col("product_id")).alias("product_id"),
                col("quantity").cast("integer").alias("quantity"),
                col("total_amount").cast("double").alias("total_amount"),
                trim(col("order_status")).alias("order_status"),
                trim(col("payment_method")).alias("payment_method"),
                to_timestamp(col("order_date")).alias("order_date"),
                trim(col("shipping_address")).alias("shipping_address"),
                col("_ingested_at"),
                col("_source_file")
            ).dropDuplicates(["order_id"])

            # Run DQ checks
            logger.info("Executing Data Quality checks on orders...")
            null_res = self.dq.run_null_check(df_clean, ["order_id", "customer_id", "product_id"])
            range_res = self.dq.run_range_check(df_clean, "quantity", 1, 100)
            pk_res = self.dq.run_uniqueness_check(df_clean, ["order_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, Range: {range_res['pass']}, PK: {pk_res['pass']}")

            df_clean.write.format("delta").mode("overwrite").save(str(self.silver_orders_path))
            logger.info(f"Orders saved to Silver Delta: {self.silver_orders_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_bronze = bronze_utils.load_fallback_df(self.bronze_orders_path)
            if df_bronze.empty:
                logger.error("No bronze data found for orders fallback processing.")
                return
            
            df_clean = df_bronze.copy()
            df_clean["order_id"] = df_clean["order_id"].astype(str).str.strip()
            df_clean["customer_id"] = df_clean["customer_id"].astype(str).str.strip()
            df_clean["product_id"] = df_clean["product_id"].astype(str).str.strip()
            df_clean["quantity"] = df_clean["quantity"].astype(int)
            df_clean["total_amount"] = df_clean["total_amount"].astype(float)
            df_clean["order_status"] = df_clean["order_status"].astype(str).str.strip()
            df_clean["payment_method"] = df_clean["payment_method"].astype(str).str.strip()
            df_clean["order_date"] = pd.to_datetime(df_clean["order_date"])
            df_clean["shipping_address"] = df_clean["shipping_address"].astype(str).str.strip()
            
            df_clean = df_clean.drop_duplicates(subset=["order_id"])

            logger.info("Executing Data Quality checks on orders (Pandas fallback)...")
            null_res = self.dq.run_null_check(df_clean, ["order_id", "customer_id", "product_id"])
            range_res = self.dq.run_range_check(df_clean, "quantity", 1, 100)
            pk_res = self.dq.run_uniqueness_check(df_clean, ["order_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, Range: {range_res['pass']}, PK: {pk_res['pass']}")

            bronze_utils.save_fallback_df(df_clean, self.silver_orders_path)

        logger.info("Silver orders processing completed successfully.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = SilverOrdersProcessor(cfg)
    processor.process()
