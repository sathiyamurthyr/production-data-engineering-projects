import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils
from src.silver.data_quality_checks import DataQualityChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SilverEventsProcessor:
    """Processes Bronze clickstream events into clean Silver format."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.bronze_events_path = Path(self.storage_cfg.get("bronze_path")) / "events"
        self.silver_events_path = Path(self.storage_cfg.get("silver_path")) / "events"
        self.spark = bronze_utils.get_spark_session(self.config)
        self.dq = DataQualityChecker(self.config)

    def process(self):
        logger.info("Starting Silver layer processing for events...")

        if self.spark:
            df_bronze = self.spark.read.format("delta").load(str(self.bronze_events_path))
            
            from pyspark.sql.functions import col, to_timestamp, trim
            df_clean = df_bronze.select(
                trim(col("event_id")).alias("event_id"),
                trim(col("customer_id")).alias("customer_id"),
                trim(col("event_type")).alias("event_type"),
                trim(col("product_id")).alias("product_id"),
                to_timestamp(col("timestamp")).alias("timestamp"),
                trim(col("ip_address")).alias("ip_address"),
                trim(col("device")).alias("device"),
                trim(col("session_id")).alias("session_id"),
                col("_ingested_at"),
                col("_source_file")
            ).dropDuplicates(["event_id"])

            # Run DQ checks
            null_res = self.dq.run_null_check(df_clean, ["event_id", "event_type", "session_id"])
            pk_res = self.dq.run_uniqueness_check(df_clean, ["event_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, PK: {pk_res['pass']}")

            df_clean.write.format("delta").mode("overwrite").save(str(self.silver_events_path))
            logger.info(f"Events saved to Silver Delta: {self.silver_events_path}")
        else:
            logger.info("Executing local fallback using Pandas...")
            import pandas as pd
            df_bronze = bronze_utils.load_fallback_df(self.bronze_events_path)
            if df_bronze.empty:
                logger.error("No bronze data found for events fallback processing.")
                return
            
            df_clean = df_bronze.copy()
            df_clean["event_id"] = df_clean["event_id"].astype(str).str.strip()
            df_clean["customer_id"] = df_clean["customer_id"].apply(lambda x: str(x).strip() if pd.notnull(x) else None)
            df_clean["event_type"] = df_clean["event_type"].astype(str).str.strip()
            df_clean["product_id"] = df_clean["product_id"].apply(lambda x: str(x).strip() if pd.notnull(x) else None)
            df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"])
            df_clean["ip_address"] = df_clean["ip_address"].astype(str).str.strip()
            df_clean["device"] = df_clean["device"].astype(str).str.strip()
            df_clean["session_id"] = df_clean["session_id"].astype(str).str.strip()
            
            df_clean = df_clean.drop_duplicates(subset=["event_id"])

            logger.info("Executing Data Quality checks on events (Pandas fallback)...")
            null_res = self.dq.run_null_check(df_clean, ["event_id", "event_type", "session_id"])
            pk_res = self.dq.run_uniqueness_check(df_clean, ["event_id"])
            logger.info(f"DQ checks summary - Nulls: {null_res['pass']}, PK: {pk_res['pass']}")

            bronze_utils.save_fallback_df(df_clean, self.silver_events_path)

        logger.info("Silver events processing completed successfully.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    processor = SilverEventsProcessor(cfg)
    processor.process()
