import csv
import logging
from pathlib import Path
from datetime import datetime
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class CostTracker:
    """Calculates and logs estimated Spark compute (DBUs) and Snowflake credit cost telemetry."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.base_storage = Path(self.config.storage_config.get("base_path"))
        self.telemetry_file = self.base_storage / "telemetry" / "platform_costs.csv"

        # Pricing unit assumptions
        self.usd_per_snowflake_credit = 3.00
        self.usd_per_databricks_dbu = 0.40
        
        # Consumption speeds (per second)
        self.snowflake_credits_per_second = (2.0 / 3600.0)  # Medium warehouse uses 4 credits/hour, Small uses 2
        self.databricks_dbus_per_second = (4.0 / 3600.0)      # Standard node uses 4 DBUs/hour

    def track_run_cost(self, job_name: str, duration_seconds: float, platform: str = "spark"):
        """Logs and calculates execution cost estimates for the pipeline runs."""
        logger.info(f"Tracking run cost for job={job_name}, platform={platform}, duration={duration_seconds}s")
        
        self.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.telemetry_file.exists()

        headers = ["timestamp", "job_name", "platform", "duration_seconds", "estimated_units", "estimated_cost_usd"]

        if platform.lower() == "snowflake":
            units = duration_seconds * self.snowflake_credits_per_second
            cost = units * self.usd_per_snowflake_credit
        else:  # default to spark
            units = duration_seconds * self.databricks_dbus_per_second
            cost = units * self.usd_per_databricks_dbu

        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "job_name": job_name,
            "platform": platform,
            "duration_seconds": round(duration_seconds, 2),
            "estimated_units": round(units, 6),
            "estimated_cost_usd": round(cost, 4)
        }

        try:
            with open(self.telemetry_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            logger.info("Cost telemetry logged successfully.")
        except Exception as e:
            logger.error(f"Failed to write cost telemetry: {e}")

if __name__ == "__main__":
    cfg = PipelineConfig()
    tracker = CostTracker(cfg)
    tracker.track_run_cost("BronzeOrdersJob", 120.5, "spark")
    tracker.track_run_cost("GoldFactOrdersJob", 45.0, "snowflake")
