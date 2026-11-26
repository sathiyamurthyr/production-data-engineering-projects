import logging
import shutil
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ProductCatalogLoader:
    """Simulates loading product catalog updates to the landing zone."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.landing_dir = self.base_storage / "landing" / "products"
        self.sample_products_file = Path(self.config.config_path).parent.parent / "sample-data" / "products.csv"

    def load(self) -> str:
        """Loads product catalog into the landing path."""
        logger.info("Starting product catalog ingestion...")
        
        self.landing_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.sample_products_file.exists():
            raise FileNotFoundError(f"Sample products file not found at: {self.sample_products_file}")

        target_file = self.landing_dir / "products.csv"
        
        logger.info(f"Copying product catalog to landing zone path: {target_file}")
        shutil.copy(self.sample_products_file, target_file)
        
        logger.info("Product catalog ingestion completed successfully.")
        return str(target_file)

if __name__ == "__main__":
    cfg = PipelineConfig()
    loader = ProductCatalogLoader(cfg)
    loader.load()
