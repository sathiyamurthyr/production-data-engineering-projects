import json
import logging
import time
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Attempt to import kafka, handle missing library gracefully
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python-ng is not installed or import failed. Falling back to local file streaming.")

class EventsProducer:
    """Ingests clickstream events and publishes them to Kafka (or falls back to landing folder)."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.kafka_settings = self.config.kafka_config
        self.topic = self.kafka_settings.get("topics", {}).get("events", "datamart.events")
        self.bootstrap_servers = self.kafka_settings.get("bootstrap_servers", ["localhost:9092"])
        
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.landing_dir = self.base_storage / "landing" / "events"
        self.sample_events_file = Path(self.config.config_path).parent.parent / "sample-data" / "events.json"
        
        self.producer = None
        if KAFKA_AVAILABLE:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=5000,
                    max_block_ms=5000
                )
                logger.info(f"Connected to Kafka bootstrap servers: {self.bootstrap_servers}")
            except Exception as e:
                logger.warning(f"Failed to connect to Kafka broker: {e}. Running in local fallback mode.")

    def produce(self):
        """Simulates clickstream events pipeline by producing events to Kafka or landing directory."""
        logger.info("Starting clickstream events ingestion...")
        
        if not self.sample_events_file.exists():
            raise FileNotFoundError(f"Sample events file not found at: {self.sample_events_file}")

        events = []
        with open(self.sample_events_file, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line.strip()))

        if self.producer:
            logger.info(f"Publishing {len(events)} events to Kafka topic '{self.topic}'...")
            for idx, event in enumerate(events):
                event['produced_at'] = int(time.time() * 1000)
                self.producer.send(self.topic, value=event)
                if idx % 5 == 0:
                    logger.info(f"Published {idx + 1} events to Kafka.")
            self.producer.flush()
            logger.info("Successfully flushed events to Kafka.")
        else:
            # Local fallback - write to landing/events/
            self.landing_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            fallback_file = self.landing_dir / f"events_{timestamp}.json"
            logger.info(f"Fallback mode: Writing events to landing directory: {fallback_file}")
            
            with open(fallback_file, "w") as f:
                for event in events:
                    event['produced_at'] = timestamp * 1000
                    f.write(json.dumps(event) + "\n")
            logger.info("Successfully wrote events in landing zone.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    producer = EventsProducer(cfg)
    producer.produce()
