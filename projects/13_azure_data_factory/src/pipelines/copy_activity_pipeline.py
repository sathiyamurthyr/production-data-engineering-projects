"""
copy_activity_pipeline.py - Azure Data Factory Copy Activity Pipeline Manager
================================================================================
Production-grade Copy Activity pipeline creation, parameterization, and execution.

Explanation:
    Copy Activity is ADF's high-performance data movement engine capable of transferring data
    between 90+ data stores. This module builds pipelines for:
    1. Blob to ADLS Gen2 (File transfer & format conversion)
    2. REST API to Storage (Paginated API response ingestion)
    3. Azure SQL Database to Parquet (Relational extraction with custom query & column mapping)

Business Use Case:
    Raw landing zone ingestion requires automated batch copy pipelines with column mapping,
    data type coercion, retry logic, and fault tolerance. Incremental loading uses watermark
    queries to pull only modified records.

Production Example:
    mgr = CopyActivityPipelineManager(adf_client)
    run_id = mgr.create_and_run_sql_to_parquet(
        resource_group="my-rg", factory_name="my-adf",
        pipeline_name="PL_Ingest_Sales_SQL",
        sql_dataset="SqlSourceDS", parquet_dataset="ParquetSinkDS"
    )

Interview Questions:
    Q: What are Data Integration Units (DIUs) in Copy Activity?
    A: A DIU is a measure that represents the power (CPU, memory, network allocation) of a single unit
       in ADF. Increasing DIUs (e.g. from Auto/4 up to 256) scales out parallel copy throughput for large datasets.

    Q: How do you handle schema drift or column renaming during Copy Activity?
    A: Use explicit column mapping (translator) in the Copy Activity definition to map source columns
       to sink columns by name or ordinal position.
"""

import logging, uuid
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class CopyActivityPipelineManager:
    """
    Manager for creating and executing ADF Copy Activity pipelines.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def build_blob_to_adls_pipeline_spec(
        self,
        pipeline_name: str,
        source_dataset_name: str,
        sink_dataset_name: str,
        diu_count: int = 4,
        parallel_copies: int = 4,
    ) -> Dict[str, Any]:
        """
        Build pipeline specification dictionary for Blob to ADLS Gen2 Copy Activity.

        Args:
            pipeline_name: Pipeline name
            source_dataset_name: Source Blob Dataset name
            sink_dataset_name: Target ADLS Gen2 Dataset name
            diu_count: Data Integration Units (DIU) count
            parallel_copies: Maximum degree of parallel copies

        Returns:
            Pipeline specification JSON payload
        """
        return {
            "properties": {
                "description": "Copy raw files from Azure Blob Storage to ADLS Gen2 Raw Zone",
                "parameters": {
                    "SourceContainer": {"type": "String", "defaultValue": "raw"},
                    "SourceFolderPath": {"type": "String", "defaultValue": "incoming"},
                    "SinkContainer": {"type": "String", "defaultValue": "bronze"},
                    "SinkFolderPath": {"type": "String", "defaultValue": "landing"},
                },
                "activities": [
                    {
                        "name": "CopyBlobToADLS",
                        "type": "Copy",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.12:00:00",
                            "retry": 3,
                            "retryIntervalInSeconds": 30,
                            "secureOutput": False,
                            "secureInput": False,
                        },
                        "typeProperties": {
                            "source": {
                                "type": "DelimitedTextSource",
                                "storeSettings": {
                                    "type": "AzureBlobStorageReadSettings",
                                    "recursive": True,
                                    "wildcardFileName": "*.csv",
                                },
                                "formatSettings": {
                                    "type": "DelimitedTextReadSettings",
                                },
                            },
                            "sink": {
                                "type": "ParquetSink",
                                "storeSettings": {
                                    "type": "AzureBlobFSWriteSettings",
                                },
                                "formatSettings": {
                                    "type": "ParquetWriteSettings",
                                },
                            },
                            "enableStaging": False,
                            "dataIntegrationUnits": diu_count,
                            "parallelCopies": parallel_copies,
                        },
                        "inputs": [
                            {
                                "referenceName": source_dataset_name,
                                "type": "DatasetReference",
                                "parameters": {
                                    "Container": "@pipeline().parameters.SourceContainer",
                                    "FolderPath": "@pipeline().parameters.SourceFolderPath",
                                },
                            }
                        ],
                        "outputs": [
                            {
                                "referenceName": sink_dataset_name,
                                "type": "DatasetReference",
                                "parameters": {
                                    "Container": "@pipeline().parameters.SinkContainer",
                                    "FolderPath": "@pipeline().parameters.SinkFolderPath",
                                },
                            }
                        ],
                    }
                ],
            }
        }

    def build_sql_to_parquet_pipeline_spec(
        self,
        pipeline_name: str,
        sql_dataset_name: str,
        parquet_dataset_name: str,
        sql_query: Optional[str] = None,
        column_mappings: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Build pipeline specification for Azure SQL to Parquet Copy Activity with explicit column mapping.

        Args:
            pipeline_name: Name of pipeline
            sql_dataset_name: Source SQL dataset
            parquet_dataset_name: Target Parquet dataset
            sql_query: Custom SQL query for extraction
            column_mappings: Column mapping list e.g. [{'source': 'Customer_ID', 'target': 'customer_id'}]

        Returns:
            Pipeline payload dict
        """
        query_expr = sql_query or "SELECT * FROM @{pipeline().parameters.SchemaName}.@{pipeline().parameters.TableName} WHERE is_active = 1"

        translator_mappings = []
        if column_mappings:
            for item in column_mappings:
                translator_mappings.append({
                    "source": {"name": item["source"]},
                    "sink": {"name": item["target"]},
                })

        translator_config = {
            "type": "TabularTranslator",
            "mappings": translator_mappings,
        } if translator_mappings else {"type": "TabularTranslator"}

        return {
            "properties": {
                "description": "Extract relational tables from Azure SQL to Parquet storage",
                "parameters": {
                    "SchemaName": {"type": "String", "defaultValue": "dbo"},
                    "TableName": {"type": "String", "defaultValue": "Orders"},
                    "WatermarkValue": {"type": "String", "defaultValue": "1970-01-01 00:00:00"},
                },
                "activities": [
                    {
                        "name": "CopySqlToParquet",
                        "type": "Copy",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.04:00:00",
                            "retry": 2,
                            "retryIntervalInSeconds": 60,
                        },
                        "typeProperties": {
                            "source": {
                                "type": "AzureSqlSource",
                                "sqlReaderQuery": query_expr,
                                "queryTimeout": "02:00:00",
                                "partitionOption": "None",
                            },
                            "sink": {
                                "type": "ParquetSink",
                                "storeSettings": {"type": "AzureBlobFSWriteSettings"},
                                "formatSettings": {"type": "ParquetWriteSettings"},
                            },
                            "translator": translator_config,
                        },
                        "inputs": [
                            {
                                "referenceName": sql_dataset_name,
                                "type": "DatasetReference",
                                "parameters": {
                                    "SchemaName": "@pipeline().parameters.SchemaName",
                                    "TableName": "@pipeline().parameters.TableName",
                                },
                            }
                        ],
                        "outputs": [
                            {
                                "referenceName": parquet_dataset_name,
                                "type": "DatasetReference",
                            }
                        ],
                    }
                ],
            }
        }

    def create_or_update_pipeline(
        self,
        resource_group: str,
        factory_name: str,
        pipeline_name: str,
        pipeline_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deploy or update pipeline definition in Azure Data Factory.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            pipeline_name: Pipeline name
            pipeline_spec: Full pipeline dictionary specification

        Returns:
            Created pipeline metadata
        """
        logger.info("Deploying Pipeline: %s to %s/%s", pipeline_name, resource_group, factory_name)

        if self.client.config.mock_mode:
            logger.info("Mock mode: Pipeline %s deployed successfully", pipeline_name)
            return {"name": pipeline_name, "id": f"mock-pipeline-id-{pipeline_name}", "status": "Deployed"}

        adf = self.client.get_management_client()
        result = adf.pipelines.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            pipeline_name=pipeline_name,
            pipeline=pipeline_spec,
        )
        return {"name": result.name, "id": result.id}

    def trigger_pipeline_run(
        self,
        resource_group: str,
        factory_name: str,
        pipeline_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Trigger an execution run of a deployed pipeline.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            pipeline_name: Pipeline name to trigger
            parameters: Runtime parameters to pass to execution

        Returns:
            Unique Pipeline Run ID string
        """
        params = parameters or {}
        logger.info("Triggering Pipeline run for %s with params: %s", pipeline_name, params)

        if self.client.config.mock_mode:
            mock_run_id = f"run-{uuid.uuid4()}"
            logger.info("Mock mode: Triggered run ID %s", mock_run_id)
            return mock_run_id

        adf = self.client.get_management_client()
        run_response = adf.pipelines.create_run(
            resource_group_name=resource_group,
            factory_name=factory_name,
            pipeline_name=pipeline_name,
            parameters=params,
        )
        logger.info("Pipeline run started successfully. Run ID: %s", run_response.run_id)
        return run_response.run_id
