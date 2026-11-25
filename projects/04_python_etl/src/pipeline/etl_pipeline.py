"""
Main ETL Pipeline Orchestrator linking Extractors, Transformers, and Loaders.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

from src.extractors.csv_extractor import CSVExtractor
from src.extractors.json_extractor import JSONExtractor
from src.extractors.api_extractor import APIExtractor
from src.extractors.database_extractor import DatabaseExtractor
from src.transformers.data_cleaner import DataCleaner
from src.transformers.data_enricher import DataEnricher
from src.transformers.data_validator import DataValidator
from src.transformers.aggregator import DataAggregator
from src.loaders.csv_loader import CSVLoader
from src.loaders.parquet_loader import ParquetLoader
from src.loaders.database_loader import DatabaseLoader
from src.pipeline.pipeline_config import PipelineConfig
from src.pipeline.pipeline_logger import setup_logger


class ETLPipelineExecutionError(Exception):
    """Raised when pipeline orchestration encounters a breaking error."""
    pass


class ETLPipeline:
    """Production ETL Pipeline Orchestrator."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize ETL Pipeline with a validated configuration object.

        Args:
            config: PipelineConfig instance containing all pipeline component parameters.
        """
        self.config = config
        p_settings = config.pipeline_settings
        self.logger = setup_logger(
            name=p_settings.get("name", "etl_pipeline"),
            log_level=p_settings.get("log_level", "INFO"),
            log_file=p_settings.get("log_file"),
        )
        self.metrics: Dict[str, Any] = {
            "pipeline_name": p_settings.get("name", "etl_pipeline"),
            "status": "NOT_STARTED",
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0.0,
            "records_extracted": 0,
            "records_transformed": 0,
            "records_loaded": 0,
            "errors": [],
        }

    def run(self) -> Dict[str, Any]:
        """
        Execute the end-to-end Extract, Transform, and Load pipeline workflow.

        Returns:
            Dict[str, Any]: Execution metrics and summary statistics report.

        Raises:
            ETLPipelineExecutionError: If pipeline execution fails.
        """
        start_ts = time.time()
        self.metrics["start_time"] = datetime.now(timezone.utc).isoformat()
        self.metrics["status"] = "RUNNING"
        self.logger.info(f"Starting ETL Pipeline '{self.metrics['pipeline_name']}'...")

        try:
            # ----------------------------------------------------
            # 1. EXTRACTION PHASE
            # ----------------------------------------------------
            self.logger.info("--- Phase 1: Data Extraction ---")
            extracted_dfs: Dict[str, pd.DataFrame] = {}
            for name, ext_cfg in self.config.extractors_config.items():
                ext_type = ext_cfg.get("type", "").lower()
                if ext_type == "csv":
                    extractor = CSVExtractor(ext_cfg)
                elif ext_type == "json":
                    extractor = JSONExtractor(ext_cfg)
                elif ext_type == "api":
                    extractor = APIExtractor(ext_cfg)
                elif ext_type == "database":
                    extractor = DatabaseExtractor(ext_cfg)
                else:
                    raise ETLPipelineExecutionError(f"Unsupported extractor type: '{ext_type}'")

                df_ext = extractor.extract()
                extracted_dfs[name] = df_ext
                count = len(df_ext)
                self.metrics["records_extracted"] += count
                self.logger.info(f"Extractor '{name}' yielded {count} rows.")

            # ----------------------------------------------------
            # 2. TRANSFORMATION PHASE
            # ----------------------------------------------------
            self.logger.info("--- Phase 2: Data Transformation ---")
            cleaned_dfs: Dict[str, pd.DataFrame] = {}
            tf_cfg = self.config.transformers_config

            cleaner = DataCleaner(tf_cfg.get("cleaning", {}))
            enricher = DataEnricher(tf_cfg.get("enrichment", {}))
            validator = DataValidator(tf_cfg.get("validation", {}))

            for name, df in extracted_dfs.items():
                self.logger.info(f"Processing transformations for dataset '{name}'...")
                df_clean = cleaner.transform(df)
                df_enriched = enricher.transform(df_clean)
                df_valid = validator.transform(df_enriched)
                cleaned_dfs[name] = df_valid
                self.metrics["records_transformed"] += len(df_valid)

            # ----------------------------------------------------
            # 3. AGGREGATION PHASE
            # ----------------------------------------------------
            self.logger.info("--- Phase 3: Analytical Aggregation ---")
            # If customers dataset is available, calculate aggregated metrics by country
            agg_summary_df = None
            if "customers_csv" in cleaned_dfs and not cleaned_dfs["customers_csv"].empty:
                aggregator = DataAggregator({
                    "group_by_columns": ["country"],
                    "aggregations": {"total_spent": ["sum", "mean", "count"]}
                })
                agg_summary_df = aggregator.transform(cleaned_dfs["customers_csv"])
                self.logger.info(f"Generated country revenue aggregations with {len(agg_summary_df)} summary rows.")

            # ----------------------------------------------------
            # 4. LOADING PHASE
            # ----------------------------------------------------
            self.logger.info("--- Phase 4: Data Loading ---")
            loaders_cfg = self.config.loaders_config

            for loader_name, l_cfg in loaders_cfg.items():
                l_type = l_cfg.get("type", "").lower()
                
                # Pick matching dataset for loading target
                if "customer" in loader_name and "customers_csv" in cleaned_dfs:
                    target_df = cleaned_dfs["customers_csv"]
                elif "order" in loader_name and "orders_json" in cleaned_dfs:
                    target_df = cleaned_dfs["orders_json"]
                elif "summary" in loader_name and agg_summary_df is not None:
                    target_df = agg_summary_df
                elif "sqlite_db" in loader_name:
                    # Database loader handling multiple tables if configured
                    target_df = cleaned_dfs.get("customers_csv", pd.DataFrame())
                else:
                    target_df = list(cleaned_dfs.values())[0] if cleaned_dfs else pd.DataFrame()

                if l_type == "csv":
                    loader = CSVLoader(l_cfg)
                elif l_type == "parquet":
                    loader = ParquetLoader(l_cfg)
                elif l_type == "database":
                    tables = l_cfg.get("tables", {})
                    # Load multiple tables if defined in config
                    if tables:
                        db_conn = l_cfg.get("connection_string", "sqlite:///output/etl_warehouse.db")
                        if "customers" in tables and "customers_csv" in cleaned_dfs:
                            DatabaseLoader({"connection_string": db_conn, "table_name": tables["customers"], "if_exists": "replace"}).load(cleaned_dfs["customers_csv"])
                        if "orders" in tables and "orders_json" in cleaned_dfs:
                            DatabaseLoader({"connection_string": db_conn, "table_name": tables["orders"], "if_exists": "replace"}).load(cleaned_dfs["orders_json"])
                        if "summary" in tables and agg_summary_df is not None:
                            DatabaseLoader({"connection_string": db_conn, "table_name": tables["summary"], "if_exists": "replace"}).load(agg_summary_df)
                        self.metrics["records_loaded"] += len(target_df)
                        continue
                    else:
                        loader = DatabaseLoader(l_cfg)
                else:
                    raise ETLPipelineExecutionError(f"Unsupported loader type: '{l_type}'")

                if not target_df.empty:
                    loader.load(target_df)
                    self.metrics["records_loaded"] += len(target_df)

            self.metrics["status"] = "SUCCESS"
            self.logger.info("ETL Pipeline completed successfully.")

        except Exception as e:
            self.metrics["status"] = "FAILED"
            self.metrics["errors"].append(str(e))
            self.logger.error(f"ETL Pipeline execution failed: {str(e)}")
            raise ETLPipelineExecutionError(f"Pipeline execution aborted: {str(e)}") from e

        finally:
            end_ts = time.time()
            self.metrics["end_time"] = datetime.now(timezone.utc).isoformat()
            self.metrics["duration_seconds"] = round(end_ts - start_ts, 4)
            self.logger.info(
                f"Pipeline execution finished in {self.metrics['duration_seconds']}s with status {self.metrics['status']}."
            )

        return self.metrics
