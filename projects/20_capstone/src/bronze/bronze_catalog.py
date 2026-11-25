import os
import json
import logging
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class BronzeCatalogIngestor:
    """Ingests raw static/dimension sources (Products & Customers) from landing to Bronze Delta Lake."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.storage_cfg = self.config.storage_config
        self.landing_products = Path(self.storage_cfg.get("base_path")) / "landing" / "products" / "products.csv"
        self.landing_customers = Path(self.storage_cfg.get("base_path")) / "landing" / "customers" / "customers_api_response.json"
        
        self.bronze_products_path = Path(self.storage_cfg.get("bronze_path")) / "products"
        self.bronze_customers_path = Path(self.storage_cfg.get("bronze_path")) / "customers"
        self.spark = bronze_utils.get_spark_session(self.config)

    def ingest_products(self):
        """Processes products catalog into Bronze."""
        logger.info("Ingesting products catalog to Bronze...")
        
        source_file = self.landing_products
        if not source_file.exists():
            sample_file = Path(self.config.config_path).parent.parent / "sample-data" / "products.csv"
            if sample_file.exists():
                source_file = sample_file
            else:
                logger.error("No product catalog source found.")
                return

        logger.info(f"Ingesting products from: {source_file}")

        if self.spark:
            df = self.spark.read.option("header", "true").option("inferSchema", "true").csv(str(source_file))
            df_with_meta = bronze_utils.add_ingestion_metadata(df, str(source_file))
            bronze_utils.write_to_delta(df_with_meta, str(self.bronze_products_path), mode="overwrite")
        else:
            logger.info("Executing local fallback for products using Pandas...")
            import pandas as pd
            df = pd.read_csv(source_file)
            df["_ingested_at"] = pd.Timestamp.now()
            df["_source_file"] = str(source_file)
            
            bronze_utils.save_fallback_df(df, self.bronze_products_path)

    def ingest_customers(self):
        """Processes API response customer payload into Bronze."""
        logger.info("Ingesting customer records to Bronze...")
        
        source_file = self.landing_customers
        if not source_file.exists():
            sample_file = Path(self.config.config_path).parent.parent / "sample-data" / "customers.csv"
            if sample_file.exists():
                logger.info(f"Using sample customers file to generate raw customer JSON for Bronze: {sample_file}")
                import pandas as pd
                df_raw = pd.read_csv(sample_file)
                records = df_raw.to_dict(orient="records")
                payload = {"data": records}
                source_file = Path(self.config.config_path).parent.parent / "sample-data" / "customers_mock_api.json"
                with open(source_file, "w") as f:
                    json.dump(payload, f)
            else:
                logger.error("No customer records source found.")
                return

        logger.info(f"Ingesting customers from: {source_file}")

        if self.spark:
            df_raw = self.spark.read.option("multiLine", "true").json(str(source_file))
            if "data" in df_raw.columns:
                from pyspark.sql.functions import explode
                df_exploded = df_raw.select(explode("data").alias("customer"))
                customer_fields = df_exploded.select("customer.*")
                df_with_meta = bronze_utils.add_ingestion_metadata(customer_fields, str(source_file))
                bronze_utils.write_to_delta(df_with_meta, str(self.bronze_customers_path), mode="overwrite")
            else:
                df_with_meta = bronze_utils.add_ingestion_metadata(df_raw, str(source_file))
                bronze_utils.write_to_delta(df_with_meta, str(self.bronze_customers_path), mode="overwrite")
        else:
            logger.info("Executing local fallback for customers using Pandas...")
            import pandas as pd
            with open(source_file, "r") as f:
                data = json.load(f)
            records = data.get("data", data)
            df = pd.DataFrame(records)
            df["_ingested_at"] = pd.Timestamp.now()
            df["_source_file"] = str(source_file)
            
            bronze_utils.save_fallback_df(df, self.bronze_customers_path)

    def ingest(self):
        self.ingest_products()
        self.ingest_customers()

if __name__ == "__main__":
    cfg = PipelineConfig()
    ingestor = BronzeCatalogIngestor(cfg)
    ingestor.ingest()
