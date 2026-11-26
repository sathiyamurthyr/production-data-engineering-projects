import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class OrdersExtractor:
    """Simulates extracting orders from transaction database and saving to Landing zone."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.landing_dir = self.base_storage / "landing" / "orders"
        self.sample_orders_file = Path(self.config.config_path).parent.parent / "sample-data" / "orders.csv"

    def extract(self) -> str:
        """Extracts orders from source file and writes them to the landing folder."""
        logger.info("Starting orders extraction...")
        
        # Ensure landing directory exists
        self.landing_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.sample_orders_file.exists():
            raise FileNotFoundError(f"Sample orders file not found at: {self.sample_orders_file}")

        # Construct target landing file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = self.landing_dir / f"orders_{timestamp}.csv"
        
        logger.info(f"Copying operational orders to landing path: {target_file}")
        shutil.copy(self.sample_orders_file, target_file)
        
        logger.info("Orders extraction completed successfully.")
        return str(target_file)

if __name__ == "__main__":
    cfg = PipelineConfig()
    extractor = OrdersExtractor(cfg)
    extractor.extract()
