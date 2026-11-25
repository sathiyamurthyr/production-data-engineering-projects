import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldDimCustomersProcessor:
    """Processes Silver customer records to build the Customer Dimension table in Gold."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.silver_customers_path = Path(self.storage_cfg.get("silver_path")) / "customers"
        self.gold_customers_path = Path(self.storage_cfg.get("gold_path")) / "dim_customers"
        self.spark = bronze_utils.get_spark_session(self.config)

    def process(self):
        logger.info("Processing Gold Customer Dimension...")

        if self.spark:
            df_silver = self.spark.read.format("delta").load(str(self.silver_customers_path))
            
            from pyspark.sql.functions import lit, col
            df_dim = df_silver.select(
                "customer_id",
                "first_name",
                "last_name",
                "email",
                "phone",
                "country",
                "segment",
                "created_at",
                "updated_at"
            ).withColumn("is_active", lit(True)) \
             .withColumn("valid_from", col("created_at")) \
             .withColumn("valid_to", lit(None).cast("timestamp"))

            df_dim.write.format("delta").mode("overwrite").save(str(self.gold_customers_path))
            logger.info(f"Dim Customers saved to Gold Delta: {self.gold_customers_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_silver = bronze_utils.load_fallback_df(self.silver_customers_path)
            if df_silver.empty:
                logger.error("No silver data found for customers fallback processing.")
                return
            
            df_dim = df_silver[["customer_id", "first_name", "last_name", "email", "phone", "country", "segment", "created_at", "updated_at"]].copy()
            df_dim["is_active"] = True
            df_dim["valid_from"] = df_dim["created_at"]
            df_dim["valid_to"] = pd.NaT

            bronze_utils.save_fallback_df(df_dim, self.gold_customers_path)

        logger.info("Gold Customer Dimension processing completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = GoldDimCustomersProcessor(cfg)
    processor.process()
