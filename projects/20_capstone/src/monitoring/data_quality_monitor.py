import csv
import logging
from pathlib import Path
from datetime import datetime
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DataQualityMonitor:
    """Logs and tracks detailed data quality failure metrics and anomaly alerts over time."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.telemetry_file = self.base_storage / "telemetry" / "data_quality_runs.csv"

    def log_dq_results(self, dataset: str, check_type: str, status: str, total_checked: int, failed_count: int):
        """Appends quality checks outcomes to the quality audit log."""
        logger.info(f"Logging DQ audit: dataset={dataset}, check={check_type}, status={status}")
        
        self.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.telemetry_file.exists()
        
        headers = ["timestamp", "dataset", "check_type", "status", "total_checked", "failed_count", "failure_percentage"]
        
        failure_pct = round((failed_count / total_checked) * 100.0, 2) if total_checked > 0 else 0.0
        
        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": dataset,
            "check_type": check_type,
            "status": status,
            "total_checked": total_checked,
            "failed_count": failed_count,
            "failure_percentage": failure_pct
        }
        
        try:
            with open(self.telemetry_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            logger.info("DQ audit results logged successfully.")
        except Exception as e:
            logger.error(f"Failed to write to DQ telemetry: {e}")

if __name__ == "__main__":
    cfg = PipelineConfig()
    dq_mon = DataQualityMonitor(cfg)
    dq_mon.log_dq_results("orders", "null_check", "PASS", 100, 0)
    dq_mon.log_dq_results("products", "range_check", "FAIL", 50, 2)
