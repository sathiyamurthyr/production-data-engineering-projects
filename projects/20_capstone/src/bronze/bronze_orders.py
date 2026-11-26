import os
import glob
import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class BronzeOrdersIngestor:
    """Ingests raw orders files from the landing directory to the bronze Delta Lake table."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.landing_dir = Path(self.storage_cfg.get("base_path")) / "landing" / "orders"
        self.bronze_path = Path(self.storage_cfg.get("bronze_path")) / "orders"
        self.spark = bronze_utils.get_spark_session(self.config)

    def ingest(self):
        """Scans landing zone and writes to bronze table."""
        logger.info("Starting Bronze ingestion for orders...")
        
        search_pattern = str(self.landing_dir / "*.csv")
        files = glob.glob(search_pattern)
        
        if not files:
            logger.warning(f"No files found in landing directory: {self.landing_dir}")
            sample_file = Path(self.config.config_path).parent.parent / "sample-data" / "orders.csv"
            if sample_file.exists():
                logger.info(f"Using sample-data file for fallback ingestion: {sample_file}")
                files = [str(sample_file)]
            else:
                logger.error("No raw orders file found for processing.")
                return

        latest_file = max(files, key=os.path.getmtime)
        logger.info(f"Ingesting latest orders file: {latest_file}")

        if self.spark:
            df = self.spark.read.option("header", "true").option("inferSchema", "true").csv(latest_file)
            df_with_meta = bronze_utils.add_ingestion_metadata(df, latest_file)
            bronze_utils.write_to_delta(df_with_meta, str(self.bronze_path), mode="overwrite")
        else:
            logger.info("Executing local fallback using DuckDB/Pandas...")
            import pandas as pd
            df = pd.read_csv(latest_file)
            df["_ingested_at"] = pd.Timestamp.now()
            df["_source_file"] = latest_file
            
            bronze_utils.save_fallback_df(df, self.bronze_path)

        logger.info("Bronze orders ingestion completed successfully.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    ingestor = BronzeOrdersIngestor(cfg)
    ingestor.ingest()
