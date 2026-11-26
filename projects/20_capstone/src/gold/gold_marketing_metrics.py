import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldMarketingMetricsProcessor:
    """Processes clickstream events to compute customer engagement & conversion metrics."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.silver_events_path = Path(self.storage_cfg.get("silver_path")) / "events"
        self.gold_marketing_path = Path(self.storage_cfg.get("gold_path")) / "marketing_metrics"
        self.spark = bronze_utils.get_spark_session(self.config)

    def process(self):
        logger.info("Processing Gold Marketing Metrics...")

        if self.spark:
            df_events = self.spark.read.format("delta").load(str(self.silver_events_path))

            from pyspark.sql.functions import col, count, sum, when, round
            
            df_metrics = df_events.filter(col("customer_id").isNotNull()) \
                .groupBy("customer_id") \
                .agg(
                    count("event_id").alias("total_interactions"),
                    count(when(col("event_type") == "view_item", 1)).alias("total_pageviews"),
                    count(when(col("event_type") == "add_to_cart", 1)).alias("total_add_to_carts"),
                    count(when(col("event_type") == "purchase", 1)).alias("total_purchases")
                )

            df_metrics = df_metrics.withColumn(
                "conversion_rate",
                round(col("total_purchases") / col("total_interactions"), 4)
            )

            df_metrics.write.format("delta").mode("overwrite").save(str(self.gold_marketing_path))
            logger.info(f"Marketing Metrics saved to Gold Delta: {self.gold_marketing_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_events = bronze_utils.load_fallback_df(self.silver_events_path)
            if df_events.empty:
                logger.error("No silver events found for marketing metrics fallback processing.")
                return

            df_cust_events = df_events[df_events["customer_id"].notnull()]
            
            if df_cust_events.empty:
                logger.warning("No events found with valid customer IDs for marketing metrics.")
                df_metrics = pd.DataFrame(columns=["customer_id", "total_interactions", "total_pageviews", "total_add_to_carts", "total_purchases", "conversion_rate"])
            else:
                df_metrics = df_cust_events.groupby("customer_id").agg(
                    total_interactions=("event_id", "count"),
                    total_pageviews=("event_type", lambda x: (x == "view_item").sum()),
                    total_add_to_carts=("event_type", lambda x: (x == "add_to_cart").sum()),
                    total_purchases=("event_type", lambda x: (x == "purchase").sum())
                ).reset_index()

                df_metrics["conversion_rate"] = (df_metrics["total_purchases"] / df_metrics["total_interactions"]).round(4)

            bronze_utils.save_fallback_df(df_metrics, self.gold_marketing_path)

        logger.info("Gold Marketing Metrics processing completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = GoldMarketingMetricsProcessor(cfg)
    processor.process()
