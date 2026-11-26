import os
import csv
import time
import logging
from pathlib import Path
from datetime import datetime
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PipelineMonitor:
    """Records pipeline orchestration metrics and run metadata to the telemetry store."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.telemetry_file = self.base_storage / "telemetry" / "pipeline_runs.csv"

    def log_run(self, job_name: str, status: str, records_processed: int, duration_seconds: float, error_message: str = ""):
        """Appends a row summarizing a single job execution into the telemetry file."""
        logger.info(f"Logging telemetry for job={job_name}, status={status}, count={records_processed}")
        
        self.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_exists = self.telemetry_file.exists()
        
        headers = ["timestamp", "job_name", "status", "records_processed", "duration_seconds", "error_message"]
        
        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "job_name": job_name,
            "status": status,
            "records_processed": records_processed,
            "duration_seconds": round(duration_seconds, 3),
            "error_message": error_message
        }
        
        try:
            with open(self.telemetry_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            logger.info("Telemetry recorded successfully.")
        except Exception as e:
            logger.error(f"Failed to write to telemetry log: {e}")

class Timer:
    """Helper context manager to measure execution duration."""
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        self.duration = self.end - self.start
