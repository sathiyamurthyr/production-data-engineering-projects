"""
foreach_pipeline.py - Azure Data Factory ForEach & Parallel Execution Manager
==============================================================================
Production-grade parallel batch processing pipelines using Lookup & ForEach activities.

Explanation:
    Dynamic data orchestration requires processing lists of tables, files, or API endpoints.
    This module builds dynamic pipelines using:
    1. Lookup Activity: Queries a control table or file manifest to return a list of items.
    2. ForEach Activity: Iterates over the items in parallel (up to 50 concurrent loops) or sequentially.
    3. Execute Pipeline Activity: Triggers a worker child pipeline for each item with parameter binding.

Business Use Case:
    Ingesting 100+ database tables from an OLTP system into a Data Lake raw layer without creating
    100 separate pipelines. A single control table drives the list of tables to process, and the
    ForEach activity ingests them in parallel batches.

Production Example:
    mgr = ForEachPipelineManager(adf_client)
    spec = mgr.build_dynamic_multi_table_ingest_pipeline("PL_Ingest_All_Tables", "ControlTableDS", "PL_Child_Ingest_Table")
    mgr.create_or_update_pipeline("my-rg", "my-adf", "PL_Ingest_All_Tables", spec)

Interview Questions:
    Q: What is the maximum concurrency for a ForEach activity in ADF?
    A: ADF allows up to 50 concurrent iterations in a ForEach activity when `isSequential` is set to false.
       If sequential processing is required, set `isSequential = true` or `batchCount = 1`.

    Q: Can you nest a ForEach activity inside another ForEach activity in ADF?
    A: No, ADF does not support nested ForEach activities directly within the same pipeline.
       To achieve nested looping, invoke a child pipeline via Execute Pipeline activity inside the outer ForEach.
"""

import logging, uuid
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class ForEachPipelineManager:
    """
    Manager for creating dynamic, parallelized ForEach ADF pipelines.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def build_dynamic_multi_table_ingest_pipeline_spec(
        self,
        pipeline_name: str,
        control_table_dataset_name: str,
        child_pipeline_name: str,
        batch_count: int = 20,
        is_sequential: bool = False,
    ) -> Dict[str, Any]:
        """
        Build pipeline specification for Lookup -> ForEach parallel batch table ingestion.

        Args:
            pipeline_name: Master pipeline name
            control_table_dataset_name: Dataset pointing to metadata control table
            child_pipeline_name: Name of worker child pipeline to invoke per table
            batch_count: Maximum parallel loops (1 to 50)
            is_sequential: If True, run sequentially (one table at a time)

        Returns:
            Pipeline payload dict
        """
        return {
            "properties": {
                "description": "Master pipeline reading table list from control database and ingesting in parallel",
                "parameters": {
                    "ControlSchema": {"type": "String", "defaultValue": "config"},
                    "ControlTable": {"type": "String", "defaultValue": "IngestionControlTable"},
                },
                "activities": [
                    {
                        "name": "LookupActiveTables",
                        "type": "Lookup",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.00:30:00",
                            "retry": 2,
                            "retryIntervalInSeconds": 30,
                        },
                        "typeProperties": {
                            "source": {
                                "type": "AzureSqlSource",
                                "sqlReaderQuery": "SELECT source_schema, source_table, target_container, target_path FROM config.IngestionControlTable WHERE is_enabled = 1",
                            },
                            "dataset": {
                                "referenceName": control_table_dataset_name,
                                "type": "DatasetReference",
                            },
                            "firstRowOnly": False,
                        },
                    },
                    {
                        "name": "ForEachTableParallelIngest",
                        "type": "ForEach",
                        "dependsOn": [
                            {
                                "activity": "LookupActiveTables",
                                "dependencyConditions": ["Succeeded"],
                            }
                        ],
                        "typeProperties": {
                            "isSequential": is_sequential,
                            "batchCount": batch_count,
                            "items": {
                                "value": "@activity('LookupActiveTables').output.value",
                                "type": "Expression",
                            },
                            "activities": [
                                {
                                    "name": "InvokeChildIngestPipeline",
                                    "type": "ExecutePipeline",
                                    "dependsOn": [],
                                    "policy": {
                                        "secureInput": False,
                                        "secureOutput": False,
                                    },
                                    "typeProperties": {
                                        "pipeline": {
                                            "referenceName": child_pipeline_name,
                                            "type": "PipelineReference",
                                        },
                                        "waitOnCompletion": True,
                                        "parameters": {
                                            "SourceSchema": "@item().source_schema",
                                            "SourceTable": "@item().source_table",
                                            "TargetContainer": "@item().target_container",
                                            "TargetPath": "@item().target_path",
                                        },
                                    },
                                }
                            ],
                        },
                    },
                ],
            }
        }

    def build_file_iteration_pipeline_spec(
        self,
        pipeline_name: str,
        folder_dataset_name: str,
        batch_count: int = 10,
    ) -> Dict[str, Any]:
        """
        Build pipeline specification for GetMetadata (list files) -> ForEach -> Copy activity.

        Args:
            pipeline_name: Pipeline name
            folder_dataset_name: Dataset referencing target folder
            batch_count: Maximum parallel file copies

        Returns:
            Pipeline payload dict
        """
        return {
            "properties": {
                "description": "Pipeline listing files via GetMetadata and copying them in parallel",
                "activities": [
                    {
                        "name": "GetFileList",
                        "type": "GetMetadata",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.01:00:00",
                            "retry": 1,
                            "retryIntervalInSeconds": 30,
                        },
                        "typeProperties": {
                            "dataset": {
                                "referenceName": folder_dataset_name,
                                "type": "DatasetReference",
                            },
                            "fieldList": ["childItems"],
                        },
                    },
                    {
                        "name": "ForEachFileProcess",
                        "type": "ForEach",
                        "dependsOn": [
                            {
                                "activity": "GetFileList",
                                "dependencyConditions": ["Succeeded"],
                            }
                        ],
                        "typeProperties": {
                            "isSequential": False,
                            "batchCount": batch_count,
                            "items": {
                                "value": "@activity('GetFileList').output.childItems",
                                "type": "Expression",
                            },
                            "activities": [
                                {
                                    "name": "ProcessFile",
                                    "type": "Copy",
                                    "typeProperties": {
                                        "source": {"type": "DelimitedTextSource"},
                                        "sink": {"type": "ParquetSink"},
                                    },
                                    "inputs": [
                                        {
                                            "referenceName": folder_dataset_name,
                                            "type": "DatasetReference",
                                            "parameters": {
                                                "FileName": "@item().name",
                                            },
                                        }
                                    ],
                                    "outputs": [],
                                }
                            ],
                        },
                    },
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
        Deploy pipeline specification.
        """
        logger.info("Deploying ForEach Pipeline: %s to %s/%s", pipeline_name, resource_group, factory_name)

        if self.client.config.mock_mode:
            logger.info("Mock mode: ForEach Pipeline %s deployed successfully", pipeline_name)
            return {"name": pipeline_name, "id": f"mock-foreach-id-{pipeline_name}", "status": "Deployed"}

        adf = self.client.get_management_client()
        result = adf.pipelines.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            pipeline_name=pipeline_name,
            pipeline=pipeline_spec,
        )
        return {"name": result.name, "id": result.id}
