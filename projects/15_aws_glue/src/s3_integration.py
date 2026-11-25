import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("s3_integration")

try:
    from awsglue.dynamicframe import DynamicFrame
    GLUE_ENVIRONMENT = True
except ImportError:
    GLUE_ENVIRONMENT = False

class S3DataConnector:
    """
    Handles read/write operations from/to Amazon S3 using Glue/Spark, 
    supporting partitioning and job bookmarks.
    """
    def __init__(self, glue_context: Any):
        self.glue_context = glue_context
        # Use spark session from glue_context
        self.spark = glue_context.spark_session if hasattr(glue_context, "spark_session") else glue_context.spark_session

    def read_from_s3(
        self,
        s3_path: str,
        file_format: str = "csv",
        format_options: Optional[Dict[str, Any]] = None,
        use_bookmark: bool = True
    ) -> Any:
        """
        Reads files from S3. Under native Glue, leverages Job Bookmarks if enabled.
        Under PySpark fallback, reads directly from local file paths or mock S3 paths.
        """
        logger.info(f"Reading from S3 location: {s3_path} using format: {file_format}")
        
        # Default CSV options
        if file_format == "csv" and not format_options:
            format_options = {
                "withHeader": "true",
                "separator": ","
            }
        elif not format_options:
            format_options = {}

        if GLUE_ENVIRONMENT:
            # Native Glue implementation
            connection_options = {
                "paths": [s3_path],
                "recurse": True
            }
            # Job bookmark config
            if use_bookmark:
                # AWS Glue handles job bookmarks automatically when creating a DynamicFrame from options
                # as long as job.init() and job.commit() are called.
                pass

            return self.glue_context.create_dynamic_frame_from_options(
                connection_type="s3",
                connection_options=connection_options,
                format_options=format_options
            )
        else:
            # Local/mock fallback
            logger.info("Executing S3 read fallback for local PySpark execution.")
            # Handle potential local mock paths (e.g. converting s3:// to local relative files)
            local_path = s3_path
            if s3_path.startswith("s3://"):
                # Simulating raw bucket reading
                # For local runs, we can redirect s3://.../raw/sales/ to sample-data/sample_s3_data.csv
                # if sample-data directory is present relative to Cwd
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sample_csv_path = os.path.join(base_dir, "sample-data", "sample_s3_data.csv")
                if os.path.exists(sample_csv_path):
                    local_path = sample_csv_path
                    logger.info(f"Local file mapping: mapped {s3_path} to {local_path}")

            # Use local spark reader
            reader = self.spark.read
            for opt_key, opt_val in format_options.items():
                # Convert boolean values to strings for spark options
                if isinstance(opt_val, bool):
                    opt_val = "true" if opt_val else "false"
                reader = reader.option(opt_key, str(opt_val))

            if file_format.lower() == "csv":
                df = reader.csv(local_path)
            elif file_format.lower() == "parquet":
                df = reader.parquet(local_path)
            elif file_format.lower() == "json":
                df = reader.json(local_path)
            else:
                df = reader.load(local_path)

            from src.glue_context import MockDynamicFrame
            return MockDynamicFrame(df)

    def write_to_s3(
        self,
        dynamic_frame: Any,
        s3_path: str,
        file_format: str = "parquet",
        partition_keys: Optional[List[str]] = None,
        format_options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Writes DynamicFrame/PySpark DataFrame to S3 with partition keys.
        """
        logger.info(f"Writing dataset to S3: {s3_path} in format: {file_format} partitioned by {partition_keys}")
        
        if not format_options:
            format_options = {}

        if GLUE_ENVIRONMENT:
            connection_options = {
                "path": s3_path
            }
            if partition_keys:
                connection_options["partitionKeys"] = partition_keys

            # Use native Glue dynamic frame writer
            return self.glue_context.write_dynamic_frame.from_options(
                frame=dynamic_frame,
                connection_type="s3",
                connection_options=connection_options,
                format=file_format,
                format_options=format_options
            )
        else:
            logger.info("Executing S3 write fallback for local PySpark execution.")
            is_wrapper = hasattr(dynamic_frame, "spark_df")
            df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
            
            # Local output mapping
            local_path = s3_path
            if s3_path.startswith("s3://"):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                # Map s3://bucket/processed/sales/ to local output directory under target/processed/sales/
                local_path = os.path.join(base_dir, "target", "processed", "sales")
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                logger.info(f"Local write mapping: mapped {s3_path} to {local_path}")

            writer = df.write.mode("overwrite")
            
            if partition_keys:
                writer = writer.partitionBy(*partition_keys)
                
            for opt_key, opt_val in format_options.items():
                if isinstance(opt_val, bool):
                    opt_val = "true" if opt_val else "false"
                writer = writer.option(opt_key, str(opt_val))

            if file_format.lower() == "csv":
                writer.csv(local_path, header=True)
            elif file_format.lower() == "parquet":
                writer.parquet(local_path)
            elif file_format.lower() == "json":
                writer.json(local_path)
            else:
                writer.save(local_path)

            logger.info("Local write complete.")
            return dynamic_frame


class JobBookmarkStateTracker:
    """
    Simulates AWS Glue Job Bookmark state tracking to educate engineers on
    state markers, replay mechanisms, and incremental ETL runs.
    """
    @staticmethod
    def get_simulated_bookmark_state(job_name: str) -> Dict[str, Any]:
        """Returns dummy/simulated partition markers & state metadata."""
        return {
            "job_name": job_name,
            "bookmark_mechanism": "Glue Job Bookmarks",
            "state_storage": "AWS Glue Internal Catalog Metadata Store",
            "tracking_parameters": {
                "run_frequency": "incremental",
                "high_watermark_column": "order_date",
                "processed_partitions": [
                    "year=2026/month=07/day=20",
                    "year=2026/month=07/day=21"
                ]
            }
        }
