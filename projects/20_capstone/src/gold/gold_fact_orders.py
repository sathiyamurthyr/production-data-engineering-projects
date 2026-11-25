import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldFactOrdersProcessor:
    """Processes Silver orders to construct the core Fact Orders table in Gold."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.silver_orders_path = Path(self.storage_cfg.get("silver_path")) / "orders"
        self.silver_products_path = Path(self.storage_cfg.get("silver_path")) / "products"
        self.gold_fact_path = Path(self.storage_cfg.get("gold_path")) / "fact_orders"
        self.spark = bronze_utils.get_spark_session(self.config)

    def process(self):
        logger.info("Processing Gold Fact Orders...")

        if self.spark:
            df_orders = self.spark.read.format("delta").load(str(self.silver_orders_path))
            df_products = self.spark.read.format("delta").load(str(self.silver_products_path))

            df_joined = df_orders.join(df_products, "product_id", "inner")

            from pyspark.sql.functions import col, date_format, when, round
            
            df_fact = df_joined.select(
                col("order_id"),
                col("customer_id"),
                col("product_id"),
                date_format(col("order_date"), "yyyyMMdd").cast("integer").alias("order_date_key"),
                col("quantity"),
                col("price").alias("unit_price"),
                round(col("quantity") * col("price"), 2).alias("gross_revenue"),
                col("order_status"),
                col("payment_method"),
                col("order_date")
            )

            df_fact = df_fact.withColumn("tax_amount", round(col("gross_revenue") * 0.08, 2)) \
                             .withColumn("shipping_fee", when(col("gross_revenue") > 100.0, 0.0).otherwise(9.99))
            
            df_fact = df_fact.withColumn("net_revenue", round(col("gross_revenue") + col("tax_amount") + col("shipping_fee"), 2))

            df_fact.write.format("delta").mode("overwrite").save(str(self.gold_fact_path))
            logger.info(f"Fact Orders saved to Gold Delta: {self.gold_fact_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_orders = bronze_utils.load_fallback_df(self.silver_orders_path)
            df_products = bronze_utils.load_fallback_df(self.silver_products_path)
            if df_orders.empty or df_products.empty:
                logger.error("Missing silver data for orders/products fallback processing.")
                return

            df_joined = pd.merge(df_orders, df_products[["product_id", "price"]], on="product_id", how="inner")

            df_fact = pd.DataFrame()
            df_fact["order_id"] = df_joined["order_id"]
            df_fact["customer_id"] = df_joined["customer_id"]
            df_fact["product_id"] = df_joined["product_id"]
            df_fact["order_date_key"] = pd.to_datetime(df_joined["order_date"]).dt.strftime("%Y%m%d").astype(int)
            df_fact["quantity"] = df_joined["quantity"]
            df_fact["unit_price"] = df_joined["price"]
            df_fact["gross_revenue"] = (df_fact["quantity"] * df_fact["unit_price"]).round(2)
            df_fact["order_status"] = df_joined["order_status"]
            df_fact["payment_method"] = df_joined["payment_method"]
            df_fact["order_date"] = df_joined["order_date"]

            df_fact["tax_amount"] = (df_fact["gross_revenue"] * 0.08).round(2)
            df_fact["shipping_fee"] = df_fact["gross_revenue"].apply(lambda x: 0.0 if x > 100.0 else 9.99)
            df_fact["net_revenue"] = (df_fact["gross_revenue"] + df_fact["tax_amount"] + df_fact["shipping_fee"]).round(2)

            bronze_utils.save_fallback_df(df_fact, self.gold_fact_path)

        logger.info("Gold Fact Orders processing completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = GoldFactOrdersProcessor(cfg)
    processor.process()
