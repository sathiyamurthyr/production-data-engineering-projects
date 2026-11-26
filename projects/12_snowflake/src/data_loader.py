"""
Snowflake Data Loader Pipeline.

Provides automated data staging, file format configuration, local file uploads (PUT),
validation modes, and scalable COPY INTO commands for batch ingestion.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from src.snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class SnowflakeDataLoader:
    """Handles staging and bulk loading pipelines using Snowflake COPY INTO capabilities."""

    def __init__(self, connector: Optional[SnowflakeConnector] = None):
        self.connector = connector or SnowflakeConnector()

    def create_stage(
        self,
        stage_name: str,
        stage_type: str = "INTERNAL",
        s3_url: Optional[str] = None,
        storage_integration: Optional[str] = None,
        directory_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Create internal or external stage in Snowflake.

        :param stage_name: Identifier for the stage (e.g. RAW_INTERNAL_STAGE)
        :param stage_type: 'INTERNAL' or 'EXTERNAL'
        :param s3_url: S3 bucket URL (required for EXTERNAL)
        :param storage_integration: Storage integration name for EXTERNAL
        :param directory_enabled: Enable directory table metadata tracking
        :return: Execution summary dictionary
        """
        with self.connector as conn:
            cursor = conn.cursor()

            if stage_type.upper() == "EXTERNAL":
                if not s3_url or not storage_integration:
                    raise ValueError("External stage requires s3_url and storage_integration")
                sql = f"""
                CREATE OR REPLACE STAGE {stage_name}
                URL = '{s3_url}'
                STORAGE_INTEGRATION = {storage_integration}
                DIRECTORY = (ENABLE = {str(directory_enabled).upper()});
                """
            else:
                sql = f"""
                CREATE OR REPLACE STAGE {stage_name}
                DIRECTORY = (ENABLE = {str(directory_enabled).upper()});
                """

            logger.info("Executing DDL: %s", sql.strip())
            cursor.execute(sql)
            return {"stage_name": stage_name, "stage_type": stage_type, "status": "CREATED"}

    def create_file_format(
        self,
        format_name: str,
        format_type: str = "CSV",
        compression: str = "AUTO",
        field_delimiter: str = ",",
        skip_header: int = 1,
        strip_outer_array: bool = True,
    ) -> Dict[str, Any]:
        """
        Create reusable file format definition in Snowflake.

        :param format_name: Name of file format (e.g. CSV_HEADER_FORMAT)
        :param format_type: CSV, JSON, PARQUET, AVRO, ORC
        :param compression: AUTO, GZIP, BZ2, NONE
        :param field_delimiter: Character delimiter for CSV
        :param skip_header: Number of header lines to skip
        :param strip_outer_array: Strip outer array for JSON format
        :return: Execution status dictionary
        """
        with self.connector as conn:
            cursor = conn.cursor()
            fmt = format_type.upper()

            if fmt == "CSV":
                sql = f"""
                CREATE OR REPLACE FILE FORMAT {format_name}
                TYPE = 'CSV'
                FIELD_DELIMITER = '{field_delimiter}'
                SKIP_HEADER = {skip_header}
                COMPRESSION = '{compression}'
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                NULL_IF = ('NULL', 'null', '');
                """
            elif fmt == "JSON":
                sql = f"""
                CREATE OR REPLACE FILE FORMAT {format_name}
                TYPE = 'JSON'
                COMPRESSION = '{compression}'
                STRIP_OUTER_ARRAY = {str(strip_outer_array).upper()};
                """
            elif fmt == "PARQUET":
                sql = f"""
                CREATE OR REPLACE FILE FORMAT {format_name}
                TYPE = 'PARQUET'
                COMPRESSION = '{compression}';
                """
            else:
                raise ValueError(f"Unsupported file format type: {format_type}")

            logger.info("Creating File Format: %s", format_name)
            cursor.execute(sql)
            return {"format_name": format_name, "type": fmt, "status": "CREATED"}

    def upload_file_to_stage(self, local_file_path: str, stage_name: str) -> Dict[str, Any]:
        """
        Upload local file to Snowflake internal stage using PUT command.

        :param local_file_path: Local filesystem path to data file
        :param stage_name: Target internal stage name
        :return: Transfer status dictionary
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        # Standardize path for Windows / Snowflake PUT syntax
        clean_path = local_file_path.replace("\\", "/")
        put_sql = f"PUT file://{clean_path} @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE;"

        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Uploading %s to stage @%s", local_file_path, stage_name)
            cursor.execute(put_sql)
            return {"file": os.path.basename(local_file_path), "stage": stage_name, "status": "UPLOADED"}

    def execute_copy_into(
        self,
        target_table: str,
        stage_name: str,
        file_format_name: Optional[str] = None,
        file_pattern: Optional[str] = None,
        on_error: str = "CONTINUE",
        purge: bool = False,
        match_by_column_name: str = "CASE_INSENSITIVE",
    ) -> Dict[str, Any]:
        """
        Execute COPY INTO table command to ingest staged data.

        :param target_table: Target table identifier
        :param stage_name: Stage name containing source files
        :param file_format_name: Named file format (optional)
        :param file_pattern: Regex pattern to filter staged files (e.g. '.*sales.*\\.csv\\.gz')
        :param on_error: Error strategy ('CONTINUE', 'SKIP_FILE', 'ABORT_STATEMENT')
        :param purge: If True, deletes files from stage after successful load
        :param match_by_column_name: Auto column matching policy ('CASE_INSENSITIVE' or 'NONE')
        :return: Execution metrics summary
        """
        fmt_clause = f"FILE_FORMAT = (FORMAT_NAME = '{file_format_name}')" if file_format_name else ""
        pattern_clause = f"PATTERN = '{file_pattern}'" if file_pattern else ""
        purge_clause = f"PURGE = {str(purge).upper()}"
        match_clause = f"MATCH_BY_COLUMN_NAME = {match_by_column_name}"

        copy_sql = f"""
        COPY INTO {target_table}
        FROM @{stage_name}
        {fmt_clause}
        {pattern_clause}
        ON_ERROR = '{on_error}'
        {purge_clause}
        {match_clause};
        """

        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Executing COPY INTO %s from @%s", target_table, stage_name)
            cursor.execute(copy_sql)
            results = cursor.fetchall()
            return {
                "target_table": target_table,
                "stage": stage_name,
                "status": "COMPLETED",
                "details": results,
            }

    def load_csv_pipeline(
        self,
        local_csv_path: str,
        target_table: str,
        stage_name: str = "RAW_INTERNAL_STAGE",
        format_name: str = "CSV_HEADER_FORMAT",
    ) -> Dict[str, Any]:
        """End-to-end ingestion pipeline: Stage creation -> File upload -> COPY INTO execution."""
        logger.info("Starting end-to-end load pipeline for %s", local_csv_path)
        self.create_stage(stage_name=stage_name)
        self.create_file_format(format_name=format_name, format_type="CSV")
        upload_res = self.upload_file_to_stage(local_file_path=local_csv_path, stage_name=stage_name)
        file_name = os.path.basename(local_csv_path)
        copy_res = self.execute_copy_into(
            target_table=target_table,
            stage_name=stage_name,
            file_format_name=format_name,
            file_pattern=f".*{file_name}.*",
        )
        return {"upload": upload_res, "copy": copy_res, "pipeline_status": "SUCCESS"}
