"""
Module 45: Mini ETL Pipeline Orchestrator.
Integrates Config, Extractor, Validator, Transformer, and Loader modules.
"""

import sys
import logging
from pathlib import Path

# Add current pipeline directory to sys.path
pipeline_dir = Path(__file__).resolve().parent
if str(pipeline_dir) not in sys.path:
    sys.path.insert(0, str(pipeline_dir))

from config_loader import ConfigLoader
from extractor import DataExtractor
from validator import DataValidator
from transformer import DataTransformer
from loader import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pipeline.main")

def run_pipeline(base_dir: Path) -> int:
    """Run full end-to-end Mini ETL Pipeline."""
    logger.info("Initializing Mini ETL Pipeline...")

    config_file = base_dir / "configs/config.json"
    config = ConfigLoader(config_file)

    raw_csv = base_dir / "datasets/raw_sales.csv"
    quarantine_csv = base_dir / "datasets/invalid_records.csv"
    output_json = base_dir / "output/sales_summary.json"

    # 1. Extract
    extractor = DataExtractor()
    raw_records = extractor.extract_csv(raw_csv)

    # 2. Validate
    validator = DataValidator(quarantine_csv)
    valid_records, _ = validator.validate_transactions(raw_records)

    # 3. Transform
    transformer = DataTransformer()
    summary_data = transformer.transform_sales(valid_records)

    # 4. Load
    loader = DataLoader()
    loader.load_summary_json(summary_data, output_json)

    logger.info("Pipeline execution completed successfully.")
    return 0

if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent.parent.parent
    sys.exit(run_pipeline(current_dir))
