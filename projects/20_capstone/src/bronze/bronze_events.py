import os
import glob
import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class BronzeEventsIngestor:
    """Ingests raw clickstream events from Kafka or JSON landing files to Delta Lake."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.landing_dir = Path(self.storage_cfg.get("base_path")) / "landing" / "events"
        self.bronze_path = Path(self.storage_cfg.get("bronze_path")) / "events"
        self.checkpoint_dir = Path(self.storage_cfg.get("checkpoint_path")) / "events"
        self.spark = bronze_utils.get_spark_session(self.config)

    def ingest_stream(self):
        """Simulates or runs Spark streaming from Kafka."""
        if not self.spark:
            logger.warning("Spark not available. Streaming skipped.")
            return

        kafka_cfg = self.config.kafka_config
        bootstrap_servers = ",".join(kafka_cfg.get("bootstrap_servers", ["localhost:9092"]))
        topic = kafka_cfg.get("topics", {}).get("events", "datamart.events")

        logger.info(f"Subscribing to Spark stream from Kafka topic: {topic}...")
        try:
            df_stream = self.spark.readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", bootstrap_servers) \
                .option("subscribe", topic) \
                .option("startingOffsets", "earliest") \
                .load()

            df_json = df_stream.selectExpr("CAST(value AS STRING) as json_payload")
            df_final = df_json.withColumn("_ingested_at", current_timestamp()) \
                              .withColumn("_source_file", lit("kafka-stream"))

            query = df_final.writeStream \
                .format("delta") \
                .option("checkpointLocation", str(self.checkpoint_dir)) \
                .outputMode("append") \
                .start(str(self.bronze_path))

            logger.info("Kafka streaming query started. Waiting 5s for initialization...")
            query.awaitTermination(timeout=5)
            logger.info("Streaming query processed initial batch successfully.")
        except Exception as e:
            logger.warning(f"Failed Spark Streaming from Kafka: {e}. Falling back to Batch JSON file reading.")
            self.ingest_batch()

    def ingest_batch(self):
        """Batch-processes landing JSON files and writes to Bronze."""
        logger.info("Starting Bronze batch ingestion for clickstream events...")
        search_pattern = str(self.landing_dir / "*.json")
        files = glob.glob(search_pattern)

        if not files:
            logger.warning(f"No files found in landing directory: {self.landing_dir}")
            sample_file = Path(self.config.config_path).parent.parent / "sample-data" / "events.json"
            if sample_file.exists():
                logger.info(f"Using sample-data file for fallback ingestion: {sample_file}")
                files = [str(sample_file)]
            else:
                logger.error("No raw events file found for processing.")
                return

        latest_file = max(files, key=os.path.getmtime)
        logger.info(f"Ingesting latest events file: {latest_file}")

        if self.spark:
            df = self.spark.read.json(latest_file)
            df_with_meta = bronze_utils.add_ingestion_metadata(df, latest_file)
            bronze_utils.write_to_delta(df_with_meta, str(self.bronze_path), mode="overwrite")
        else:
            logger.info("Executing local fallback using DuckDB/Pandas...")
            import pandas as pd
            df = pd.read_json(latest_file, lines=True)
            df["_ingested_at"] = pd.Timestamp.now()
            df["_source_file"] = latest_file
            
            bronze_utils.save_fallback_df(df, self.bronze_path)

        logger.info("Bronze events ingestion completed successfully.")

    def ingest(self):
        self.ingest_batch()

if __name__ == "__main__":
    cfg = PipelineConfig()
    ingestor = BronzeEventsIngestor(cfg)
    ingestor.ingest()
