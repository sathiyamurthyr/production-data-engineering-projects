import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldSalesAnalyticsProcessor:
    """Computes high-level business metrics and daily/categorical sales summaries in Gold."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.gold_fact_path = Path(self.storage_cfg.get("gold_path")) / "fact_orders"
        self.gold_products_path = Path(self.storage_cfg.get("gold_path")) / "dim_products"
        self.gold_sales_analytics_path = Path(self.storage_cfg.get("gold_path")) / "sales_analytics"
        self.spark = bronze_utils.get_spark_session(self.config)

    def process(self):
        logger.info("Processing Gold Sales Analytics...")

        if self.spark:
            df_fact = self.spark.read.format("delta").load(str(self.gold_fact_path))
            df_prod = self.spark.read.format("delta").load(str(self.gold_products_path))

            df_sales = df_fact.join(df_prod, "product_id", "inner")

            from pyspark.sql.functions import sum, count, col, round
            
            df_category_sales = df_sales.groupBy("category") \
                .agg(
                    sum("quantity").alias("total_units_sold"),
                    round(sum("gross_revenue"), 2).alias("total_gross_revenue"),
                    round(sum("net_revenue"), 2).alias("total_net_revenue"),
                    count("order_id").alias("total_orders")
                )
            
            df_daily_sales = df_sales.groupBy("order_date") \
                .agg(
                    round(sum("net_revenue"), 2).alias("daily_net_revenue"),
                    count("order_id").alias("daily_orders")
                ).orderBy("order_date")

            df_category_sales.write.format("delta").mode("overwrite").save(str(self.gold_sales_analytics_path / "category_sales"))
            df_daily_sales.write.format("delta").mode("overwrite").save(str(self.gold_sales_analytics_path / "daily_sales"))
            logger.info("Sales analytics Delta tables written successfully.")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_fact = bronze_utils.load_fallback_df(self.gold_fact_path)
            df_prod = bronze_utils.load_fallback_df(self.gold_products_path)
            if df_fact.empty or df_prod.empty:
                logger.error("Missing gold data for sales analytics fallback processing.")
                return

            df_sales = pd.merge(df_fact, df_prod[["product_id", "category"]], on="product_id", how="inner")

            df_category_sales = df_sales.groupby("category").agg(
                total_units_sold=("quantity", "sum"),
                total_gross_revenue=("gross_revenue", "sum"),
                total_net_revenue=("net_revenue", "sum"),
                total_orders=("order_id", "count")
            ).reset_index()
            df_category_sales["total_gross_revenue"] = df_category_sales["total_gross_revenue"].round(2)
            df_category_sales["total_net_revenue"] = df_category_sales["total_net_revenue"].round(2)

            df_daily_sales = df_sales.groupby("order_date").agg(
                daily_net_revenue=("net_revenue", "sum"),
                daily_orders=("order_id", "count")
            ).reset_index()
            df_daily_sales["daily_net_revenue"] = df_daily_sales["daily_net_revenue"].round(2)
            df_daily_sales = df_daily_sales.sort_values(by="order_date")

            bronze_utils.save_fallback_df(df_category_sales, self.gold_sales_analytics_path / "category_sales")
            bronze_utils.save_fallback_df(df_daily_sales, self.gold_sales_analytics_path / "daily_sales")

        logger.info("Gold Sales Analytics processing completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = GoldSalesAnalyticsProcessor(cfg)
    processor.process()
