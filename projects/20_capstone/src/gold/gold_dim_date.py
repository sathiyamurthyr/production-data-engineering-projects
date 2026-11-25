import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GoldDimDateGenerator:
    """Generates a standard Date Dimension table for Gold reporting."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.gold_date_path = Path(self.storage_cfg.get("gold_path")) / "dim_date"
        self.spark = bronze_utils.get_spark_session(self.config)

    def generate(self):
        logger.info("Generating Date Dimension table...")
        
        start_date = "2026-01-01"
        end_date = "2026-12-31"

        if self.spark:
            df = self.spark.sql(f"""
                SELECT explode(sequence(to_date('{start_date}'), to_date('{end_date}'), interval 1 day)) as date
            """)
            
            from pyspark.sql.functions import col, year, month, dayofmonth, date_format, dayofweek
            df_dim = df.select(
                date_format(col("date"), "yyyyMMdd").cast("integer").alias("date_key"),
                col("date"),
                year(col("date")).alias("year"),
                month(col("date")).alias("month"),
                dayofmonth(col("date")).alias("day"),
                date_format(col("date"), "EEEE").alias("day_name"),
                date_format(col("date"), "MMMM").alias("month_name"),
                dayofweek(col("date")).alias("day_of_week"),
                date_format(col("date"), "q").cast("integer").alias("quarter")
            )
            
            df_dim.write.format("delta").mode("overwrite").save(str(self.gold_date_path))
            logger.info(f"Dim Date saved to Gold Delta: {self.gold_date_path}")
        else:
            # Local fallback using Pandas/Parquet/CSV
            import pandas as pd
            dates = pd.date_range(start=start_date, end=end_date)
            df_dim = pd.DataFrame({"date": dates})
            df_dim["date_key"] = df_dim["date"].dt.strftime("%Y%m%d").astype(int)
            df_dim["date"] = df_dim["date"].dt.date
            df_dim["year"] = dates.year
            df_dim["month"] = dates.month
            df_dim["day"] = dates.day
            df_dim["day_name"] = dates.day_name()
            df_dim["month_name"] = dates.month_name()
            df_dim["day_of_week"] = dates.dayofweek + 1
            df_dim["quarter"] = dates.quarter

            bronze_utils.save_fallback_df(df_dim, self.gold_date_path)

        logger.info("Gold Date Dimension generation completed.")

if __name__ == "__main__":
    cfg = PipelineConfig()
    generator = GoldDimDateGenerator(cfg)
    generator.generate()
