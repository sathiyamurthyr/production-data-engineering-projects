import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils
from src.silver.data_quality_checks import DataQualityChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SilverProductsProcessor:
    """Processes Bronze products data into clean Silver formats."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.bronze_products_path = Path(self.storage_cfg.get("bronze_path")) / "products"
        self.silver_products_path = Path(self.storage_cfg.get("silver_path")) / "products"
        self.spark = bronze_utils.get_spark_session(self.config)
        self.dq = DataQualityChecker(self.config)

    def process(self):
        logger.info("Starting Silver layer processing for products...")

        if self.spark:
            df_bronze = self.spark.read.format("delta").load(str(self.bronze_products_path))
            
            from pyspark.sql.functions import col, trim, to_timestamp
            df_clean = df_bronze.select(
                trim(col("product_id")).alias("product_id"),
                trim(col("product_name")).alias("product_name"),
                trim(col("category")).alias("category"),
                col("price").cast("double").alias("price"),
                col("stock_quantity").cast("integer").alias("stock_quantity"),
                to_timestamp(col("created_at")).alias("created_at"),
                to_timestamp(col("updated_at")).alias("updated_at"),
                col("_ingested_at"),
                col("_source_file")
            ).dropDuplicates(["product_id"])

            # DQ validations
            logger.info("Executing Data Quality checks on products...")
            null_res = self.dq.run_null_check(df_clean, ["product_id", "product_name", "price"])
            price_res = self.dq.run_range_check(df_clean, "price", 0.01, 10000.0)
            stock_res = self.dq.run_range_check(df_clean, "stock_quantity", 0, 1000000)
            pk_res = self.dq.run_uniqueness_check(df_clean, ["product_id"])

            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, Price: {price_res['pass']}, Stock: {stock_res['pass']}, PK: {pk_res['pass']}")

            # Save
            df_clean.write.format("delta").mode("overwrite").save(str(self.silver_products_path))
            logger.info(f"Products saved to Silver Delta: {self.silver_products_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_bronze = bronze_utils.load_fallback_df(self.bronze_products_path)
            if df_bronze.empty:
                logger.error("No bronze data found for products fallback processing.")
                return
            
            df_clean = df_bronze.copy()
            df_clean["product_id"] = df_clean["product_id"].astype(str).str.strip()
            df_clean["product_name"] = df_clean["product_name"].astype(str).str.strip()
            df_clean["category"] = df_clean["category"].astype(str).str.strip()
            df_clean["price"] = df_clean["price"].astype(float)
            df_clean["stock_quantity"] = df_clean["stock_quantity"].astype(int)
            df_clean["created_at"] = pd.to_datetime(df_clean["created_at"])
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"])
            
            df_clean = df_clean.drop_duplicates(subset=["product_id"])

            # DQ validations
            logger.info("Executing Data Quality checks on products (Pandas fallback)...")
            null_res = self.dq.run_null_check(df_clean, ["product_id", "product_name", "price"])
            price_res = self.dq.run_range_check(df_clean, "price", 0.01, 10000.0)
            stock_res = self.dq.run_range_check(df_clean, "stock_quantity", 0, 1000000)
            pk_res = self.dq.run_uniqueness_check(df_clean, ["product_id"])

            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, Price: {price_res['pass']}, Stock: {stock_res['pass']}, PK: {pk_res['pass']}")

            bronze_utils.save_fallback_df(df_clean, self.silver_products_path)

        logger.info("Silver products processing completed successfully.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = SilverProductsProcessor(cfg)
    processor.process()
