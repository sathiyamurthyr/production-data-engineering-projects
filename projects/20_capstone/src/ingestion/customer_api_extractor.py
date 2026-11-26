import csv
import json
import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class CustomerAPIExtractor:
    """Mocks calling an external Customer Service REST API to retrieve customer updates."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.landing_dir = self.base_storage / "landing" / "customers"
        self.sample_customers_file = Path(self.config.config_path).parent.parent / "sample-data" / "customers.csv"

    def extract(self) -> str:
        """Simulates pulling customer records from a REST endpoint and storing as JSON in landing zone."""
        logger.info("Initiating customers API extraction simulation...")
        
        self.landing_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.sample_customers_file.exists():
            raise FileNotFoundError(f"Sample customers file not found at: {self.sample_customers_file}")

        # Simulate API response payload by parsing customers.csv
        api_response_records = []
        with open(self.sample_customers_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                api_response_records.append(row)

        # Mocking an API wrapper response format
        api_payload = {
            "status": "success",
            "metadata": {
                "count": len(api_response_records),
                "extracted_at": "2026-03-31T23:59:59Z",
                "source_system": "CustomerRESTService"
            },
            "data": api_response_records
        }

        target_file = self.landing_dir / "customers_api_response.json"
        logger.info(f"Saving simulated API response to landing path: {target_file}")
        
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(api_payload, f, indent=2)

        logger.info("Customers API extraction completed successfully.")
        return str(target_file)

if __name__ == "__main__":
    cfg = PipelineConfig()
    extractor = CustomerAPIExtractor(cfg)
    extractor.extract()
