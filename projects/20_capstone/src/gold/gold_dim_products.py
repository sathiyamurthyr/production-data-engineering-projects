import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldDimProductsProcessor:
    """Creates the Product Dimension table in Gold layer."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.silver_products_path = Path(self.storage_cfg.get("silver_path")) / "products"
        self.gold_products_path = Path(self.storage_cfg.get("gold_path")) / "dim_products"
        self.spark = bronze_utils.get_spark_session(self.config)

    def process(self):
        logger.info("Processing Gold Product Dimension...")

        if self.spark:
            df_silver = self.spark.read.format("delta").load(str(self.silver_products_path))
            
            df_dim = df_silver.select(
                "product_id",
                "product_name",
                "category",
                "price",
                "stock_quantity",
                "updated_at"
            )

            df_dim.write.format("delta").mode("overwrite").save(str(self.gold_products_path))
            logger.info(f"Dim Products saved to Gold Delta: {self.gold_products_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_silver = bronze_utils.load_fallback_df(self.silver_products_path)
            if df_silver.empty:
                logger.error("No silver data found for products fallback processing.")
                return
            
            df_dim = df_silver[["product_id", "product_name", "category", "price", "stock_quantity", "updated_at"]].copy()

            bronze_utils.save_fallback_df(df_dim, self.gold_products_path)

        logger.info("Gold Product Dimension processing completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = GoldDimProductsProcessor(cfg)
    processor.process()
