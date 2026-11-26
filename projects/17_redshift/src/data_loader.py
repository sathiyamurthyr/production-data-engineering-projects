"""
Data Loader Module
==================
Generates S3 manifest files and executes COPY commands to ingest S3 datasets
into Redshift staging tables.
"""

import json
import logging
from typing import List, Dict, Any, Union
from src.redshift_connector import MockRedshiftConnection

logger = logging.getLogger(__name__)

class RedshiftDataLoader:
    """
    Constructs and runs S3-to-Redshift COPY queries, including manifest-based ingestion
    and data format handling (CSV, Parquet).
    """

    def __init__(self, db_conn: Any, iam_role_arn: str):
        self.conn = db_conn
        self.iam_role_arn = iam_role_arn

    def generate_manifest(self, s3_uris: List[str]) -> str:
        """
        Creates a JSON manifest string suitable for the Redshift COPY command.
        
        Args:
            s3_uris: List of absolute S3 file paths (e.g. ['s3://bucket/key1.csv', ...])
            
        Returns:
            JSON string formatted for Redshift manifest validation.
        """
        manifest = {
            "entries": [
                {"url": uri, "mandatory": True}
                for uri in s3_uris
            ]
        }
        return json.dumps(manifest, indent=2)

    def upload_manifest_to_s3(self, manifest_json: str, target_s3_uri: str) -> None:
        """
        Simulates uploading a manifest JSON to S3.
        In a live production environment, this would call boto3.client('s3').put_object().
        """
        logger.info(f"Simulating upload of manifest to S3 target: {target_s3_uri}")
        logger.debug(f"Manifest content:\n{manifest_json}")

    def copy_csv_from_s3(
        self,
        table_name: str,
        s3_path: str,
        delimiter: str = ",",
        ignore_header: int = 1,
        is_manifest: bool = False,
        gzip: bool = False
    ) -> None:
        """
        Executes a Redshift COPY command to load CSV data from S3.
        
        Args:
            table_name: Fully qualified target table name (e.g., 'staging.staging_sales')
            s3_path: S3 URI for target files or manifest file
            delimiter: CSV column delimiter
            ignore_header: Number of header lines to skip
            is_manifest: Whether the s3_path points to a JSON manifest file
            gzip: Whether files are Gzip compressed
        """
        manifest_clause = "MANIFEST" if is_manifest else ""
        gzip_clause = "GZIP" if gzip else ""
        
        copy_query = f"""
            COPY {table_name}
            FROM '{s3_path}'
            IAM_ROLE '{self.iam_role_arn}'
            CSV
            DELIMITER '{delimiter}'
            IGNOREHEADER {ignore_header}
            {manifest_clause}
            {gzip_clause}
            DATEFORMAT 'auto'
            TIMEFORMAT 'auto'
            TRUNCATECOLUMNS
            MAXERROR 0;
        """.strip()
        
        logger.info(f"Loading CSV data into {table_name} from S3...")
        self._execute_query(copy_query)

    def copy_parquet_from_s3(self, table_name: str, s3_path: str) -> None:
        """
        Executes a Redshift COPY command to load Parquet data from S3.
        
        Args:
            table_name: Fully qualified target table name
            s3_path: S3 prefix folder containing Parquet files
        """
        copy_query = f"""
            COPY {table_name}
            FROM '{s3_path}'
            IAM_ROLE '{self.iam_role_arn}'
            FORMAT AS PARQUET;
        """.strip()
        
        logger.info(f"Loading Parquet data into {table_name} from S3...")
        self._execute_query(copy_query)

    def _execute_query(self, query: str) -> None:
        """Helper to run a query and commit the transaction."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            self.conn.commit()
            logger.info("COPY command executed successfully.")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to execute COPY command: {e}")
            raise e
        finally:
            cursor.close()
