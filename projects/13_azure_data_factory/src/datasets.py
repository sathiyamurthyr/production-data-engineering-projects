"""
datasets.py - Azure Data Factory Dataset Specifications & Manager
===================================================================
Production-grade dataset definitions for ADF data ingestion & transformation pipelines.

Explanation:
    Datasets represent data structures within data stores that are referenced by Activities.
    A Dataset specifies:
    - Linked Service reference (how to connect)
    - Data format (Parquet, CSV, JSON, ORC, Avro, Binary, Relational Table)
    - Location parameters (container, directory, file name, schema, table name)
    - Schema mapping (column names and data types)

Business Use Case:
    Standardizing dataset definitions enables reusable pipeline patterns. Parameterized datasets
    allow a single Copy Activity or Data Flow to process hundreds of files or tables dynamically
    without creating individual pipeline definitions for each table.

Production Example:
    ds_mgr = DatasetManager(adf_client)
    ds_mgr.create_parquet_dataset(
        resource_group="my-rg", factory_name="my-adf", dataset_name="ParquetSinkDS",
        linked_service_name="ADLSGen2LS", container="gold", folder_path="curated/sales"
    )

Interview Questions:
    Q: How do you pass dynamic file names or dates into ADF Datasets?
    A: Use Dataset Parameters. Define parameter placeholders (e.g. `@dataset().FolderName`,
       `@dataset().FileName`) in the Dataset definition and supply parameter values at runtime
       from Pipeline parameters or activity outputs.

    Q: What is the benefit of using Parquet dataset format over DelimitedText (CSV)?
    A: Parquet is a columnar, compressed storage format supporting schema enforcement, predicate pushdown,
       and faster I/O performance. CSV requires full file scans and manual schema inferencing.
"""

import logging
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class DatasetManager:
    """
    Manager for creating, retrieving, listing, and managing Azure Data Factory Datasets.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize DatasetManager with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def create_parquet_dataset(
        self,
        resource_group: str,
        factory_name: str,
        dataset_name: str,
        linked_service_name: str,
        container: str,
        folder_path: Optional[str] = None,
        file_name: Optional[str] = None,
        compression_codec: str = "snappy",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Parquet format Dataset on ADLS Gen2 or Blob Storage.

        Args:
            resource_group: Azure resource group
            factory_name: ADF factory name
            dataset_name: Dataset name
            linked_service_name: Associated Linked Service reference
            container: Storage container name
            folder_path: Folder path within container
            file_name: Target file name (or dynamic expression)
            compression_codec: Compression codec ('snappy', 'gzip', 'lzo', 'uncompressed')
            parameters: Parameter definitions for dynamic dataset routing

        Returns:
            Created Dataset resource dict
        """
        logger.info("Creating Parquet Dataset: %s (LinkedService=%s)", dataset_name, linked_service_name)

        dataset_params = parameters or {
            "Container": {"type": "String", "defaultValue": container},
            "FolderPath": {"type": "String", "defaultValue": folder_path or ""},
            "FileName": {"type": "String", "defaultValue": file_name or ""},
        }

        payload = {
            "properties": {
                "type": "Parquet",
                "linkedServiceName": {
                    "referenceName": linked_service_name,
                    "type": "LinkedServiceReference",
                },
                "parameters": dataset_params,
                "typeProperties": {
                    "location": {
                        "type": "AzureBlobFSLocation",
                        "fileSystem": "@dataset().Container",
                        "folderPath": "@dataset().FolderPath",
                        "fileName": "@dataset().FileName",
                    },
                    "compressionCodec": compression_codec,
                },
                "description": "Optimized Parquet columnar dataset for analytical lakehouse layers",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Parquet Dataset %s", dataset_name)
            return {"name": dataset_name, "type": "Parquet", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.datasets.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            dataset_name=dataset_name,
            dataset=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_csv_dataset(
        self,
        resource_group: str,
        factory_name: str,
        dataset_name: str,
        linked_service_name: str,
        container: str,
        folder_path: str,
        file_name: Optional[str] = None,
        column_delimiter: str = ",",
        row_delimiter: str = "\n",
        first_row_as_header: bool = True,
        encoding_name: str = "UTF-8",
    ) -> Dict[str, Any]:
        """
        Create a DelimitedText (CSV/TSV) Dataset.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            dataset_name: Dataset name
            linked_service_name: Associated Linked Service
            container: Blob/ADLS container name
            folder_path: Folder path
            file_name: File name
            column_delimiter: Column separator character
            row_delimiter: Line break separator
            first_row_as_header: Has header row
            encoding_name: Text encoding

        Returns:
            Created Dataset resource dict
        """
        logger.info("Creating CSV Dataset: %s (Delimiter='%s')", dataset_name, column_delimiter)

        payload = {
            "properties": {
                "type": "DelimitedText",
                "linkedServiceName": {
                    "referenceName": linked_service_name,
                    "type": "LinkedServiceReference",
                },
                "parameters": {
                    "Container": {"type": "String", "defaultValue": container},
                    "FolderPath": {"type": "String", "defaultValue": folder_path},
                    "FileName": {"type": "String", "defaultValue": file_name or ""},
                },
                "typeProperties": {
                    "location": {
                        "type": "AzureBlobStorageLocation",
                        "container": "@dataset().Container",
                        "folderPath": "@dataset().FolderPath",
                        "fileName": "@dataset().FileName",
                    },
                    "columnDelimiter": column_delimiter,
                    "rowDelimiter": row_delimiter,
                    "firstRowAsHeader": first_row_as_header,
                    "encodingName": encoding_name,
                },
                "description": "Delimited text dataset for raw CSV/TSV ingestion",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created CSV Dataset %s", dataset_name)
            return {"name": dataset_name, "type": "DelimitedText", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.datasets.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            dataset_name=dataset_name,
            dataset=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_json_dataset(
        self,
        resource_group: str,
        factory_name: str,
        dataset_name: str,
        linked_service_name: str,
        container: str,
        folder_path: str,
        file_name: Optional[str] = None,
        encoding_name: str = "UTF-8",
    ) -> Dict[str, Any]:
        """
        Create a JSON format Dataset.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            dataset_name: Dataset name
            linked_service_name: Associated Linked Service
            container: Blob/ADLS container name
            folder_path: Folder path
            file_name: File name
            encoding_name: Character encoding

        Returns:
            Created Dataset resource dict
        """
        logger.info("Creating JSON Dataset: %s", dataset_name)

        payload = {
            "properties": {
                "type": "Json",
                "linkedServiceName": {
                    "referenceName": linked_service_name,
                    "type": "LinkedServiceReference",
                },
                "parameters": {
                    "Container": {"type": "String", "defaultValue": container},
                    "FolderPath": {"type": "String", "defaultValue": folder_path},
                    "FileName": {"type": "String", "defaultValue": file_name or ""},
                },
                "typeProperties": {
                    "location": {
                        "type": "AzureBlobFSLocation",
                        "fileSystem": "@dataset().Container",
                        "folderPath": "@dataset().FolderPath",
                        "fileName": "@dataset().FileName",
                    },
                    "encodingName": encoding_name,
                },
                "description": "JSON dataset for semi-structured log and REST response ingestion",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created JSON Dataset %s", dataset_name)
            return {"name": dataset_name, "type": "Json", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.datasets.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            dataset_name=dataset_name,
            dataset=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_azure_sql_table_dataset(
        self,
        resource_group: str,
        factory_name: str,
        dataset_name: str,
        linked_service_name: str,
        table_name: str,
        schema_name: str = "dbo",
    ) -> Dict[str, Any]:
        """
        Create Azure SQL Table Dataset with schema and table parameterization.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            dataset_name: Dataset name
            linked_service_name: Azure SQL Linked Service reference
            table_name: Default SQL table name
            schema_name: Default SQL schema name

        Returns:
            Created Dataset resource dict
        """
        logger.info("Creating Azure SQL Dataset: %s (Table=%s.%s)", dataset_name, schema_name, table_name)

        payload = {
            "properties": {
                "type": "AzureSqlTable",
                "linkedServiceName": {
                    "referenceName": linked_service_name,
                    "type": "LinkedServiceReference",
                },
                "parameters": {
                    "SchemaName": {"type": "String", "defaultValue": schema_name},
                    "TableName": {"type": "String", "defaultValue": table_name},
                },
                "typeProperties": {
                    "schema": "@dataset().SchemaName",
                    "table": "@dataset().TableName",
                },
                "description": "Azure SQL Table Dataset for relational OLTP source or target",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Azure SQL Dataset %s", dataset_name)
            return {"name": dataset_name, "type": "AzureSqlTable", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.datasets.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            dataset_name=dataset_name,
            dataset=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_snowflake_table_dataset(
        self,
        resource_group: str,
        factory_name: str,
        dataset_name: str,
        linked_service_name: str,
        table_name: str,
        schema_name: str = "PUBLIC",
    ) -> Dict[str, Any]:
        """
        Create Snowflake Table Dataset.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            dataset_name: Dataset name
            linked_service_name: Snowflake Linked Service
            table_name: Snowflake table name
            schema_name: Snowflake schema name

        Returns:
            Created Dataset resource dict
        """
        logger.info("Creating Snowflake Dataset: %s (Table=%s.%s)", dataset_name, schema_name, table_name)

        payload = {
            "properties": {
                "type": "SnowflakeTable",
                "linkedServiceName": {
                    "referenceName": linked_service_name,
                    "type": "LinkedServiceReference",
                },
                "parameters": {
                    "SchemaName": {"type": "String", "defaultValue": schema_name},
                    "TableName": {"type": "String", "defaultValue": table_name},
                },
                "typeProperties": {
                    "schema": "@dataset().SchemaName",
                    "table": "@dataset().TableName",
                },
                "description": "Snowflake Table Dataset for enterprise DW sink",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Snowflake Dataset %s", dataset_name)
            return {"name": dataset_name, "type": "SnowflakeTable", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.datasets.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            dataset_name=dataset_name,
            dataset=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def get_dataset(self, resource_group: str, factory_name: str, dataset_name: str) -> Dict[str, Any]:
        """
        Get an existing dataset definition.
        """
        if self.client.config.mock_mode:
            return {"name": dataset_name, "type": "Parquet"}

        adf = self.client.get_management_client()
        ds = adf.datasets.get(resource_group_name=resource_group, factory_name=factory_name, dataset_name=dataset_name)
        return {"name": ds.name, "id": ds.id, "type": ds.properties.type}

    def list_datasets(self, resource_group: str, factory_name: str) -> List[Dict[str, Any]]:
        """
        List all datasets in a factory.
        """
        if self.client.config.mock_mode:
            return [
                {"name": "ParquetSinkDS", "type": "Parquet"},
                {"name": "CsvSourceDS", "type": "DelimitedText"},
                {"name": "SqlSourceDS", "type": "AzureSqlTable"},
            ]

        adf = self.client.get_management_client()
        datasets = adf.datasets.list_by_factory(resource_group_name=resource_group, factory_name=factory_name)
        return [{"name": ds.name, "type": ds.properties.type} for ds in datasets]
