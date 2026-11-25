"""
conditional_pipeline.py - Azure Data Factory Conditional Logic Pipeline Manager
=================================================================================
Production-grade control flow and branching pipeline creation using IfCondition, Switch, and Lookup.

Explanation:
    Complex ETL workflows require decision branching, validation steps, and failure handling.
    This module implements control flow patterns using:
    1. Lookup Activity: Reads state or watermark data.
    2. IfCondition Activity: Evaluates boolean expressions `@equals(...)`, `@greater(...)`.
    3. Switch Activity: Multi-branch routing based on string expressions.
    4. Until Activity: Loop until condition evaluates to true (polling pattern).
    5. Dependency Conditions: Succeeded, Failed, Skipped, Completed activities.

Business Use Case:
    Preventing downstream processing if zero records were extracted, routing pipeline execution
    based on environment ('DEV', 'STAGING', 'PROD'), or implementing polling loops to wait for external
    file arrivals before starting Databricks or Synapse transformations.

Production Example:
    mgr = ConditionalPipelineManager(adf_client)
    spec = mgr.build_conditional_ingest_pipeline("PL_Validated_Ingest")
    mgr.create_or_update_pipeline("my-rg", "my-adf", "PL_Validated_Ingest", spec)

Interview Questions:
    Q: What dependency conditions exist between ADF activities?
    A: 1. Succeeded: Executes if preceding activity succeeded.
       2. Failed: Executes if preceding activity failed (used for error logging / alerts).
       3. Skipped: Executes if preceding activity was skipped due to conditional logic.
       4. Completed: Executes regardless of whether preceding activity succeeded or failed (cleanup tasks).

    Q: How do you handle pipeline errors and send notifications in ADF?
    A: Connect a Web Activity or Azure Logic Apps activity to the primary activity with a 'Failed'
       dependency line. The error activity receives `@activity('PrimaryActivity').error.message`
       and posts a notification to Teams/Slack or sends an email.
"""

import logging, uuid
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class ConditionalPipelineManager:
    """
    Manager for creating conditional control-flow pipelines in ADF.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def build_conditional_ingest_pipeline_spec(
        self,
        pipeline_name: str,
        lookup_dataset_name: str = "SqlSourceDS",
        child_pipeline_name: str = "PL_Process_Data",
    ) -> Dict[str, Any]:
        """
        Build pipeline with Lookup -> IfCondition (record count > 0) -> TrueBranch / FalseBranch.

        Args:
            pipeline_name: Name of pipeline
            lookup_dataset_name: Dataset to perform record count check
            child_pipeline_name: Child pipeline to execute if condition is met

        Returns:
            Pipeline payload dict
        """
        return {
            "properties": {
                "description": "Validation pipeline executing downstream ETL only when incoming record count > 0",
                "variables": {
                    "RecordCount": {"type": "String"},
                    "ExecutionStatus": {"type": "String", "defaultValue": "PENDING"},
                },
                "activities": [
                    {
                        "name": "CheckNewRecordsCount",
                        "type": "Lookup",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.00:15:00",
                            "retry": 1,
                            "retryIntervalInSeconds": 10,
                        },
                        "typeProperties": {
                            "source": {
                                "type": "AzureSqlSource",
                                "sqlReaderQuery": "SELECT COUNT(1) AS record_count FROM dbo.StagingOrders WHERE processed = 0",
                            },
                            "dataset": {
                                "referenceName": lookup_dataset_name,
                                "type": "DatasetReference",
                            },
                            "firstRowOnly": True,
                        },
                    },
                    {
                        "name": "IfRecordsExist",
                        "type": "IfCondition",
                        "dependsOn": [
                            {
                                "activity": "CheckNewRecordsCount",
                                "dependencyConditions": ["Succeeded"],
                            }
                        ],
                        "typeProperties": {
                            "expression": {
                                "value": "@greater(activity('CheckNewRecordsCount').output.firstRow.record_count, 0)",
                                "type": "Expression",
                            },
                            "ifTrueActivities": [
                                {
                                    "name": "ExecuteETLChildPipeline",
                                    "type": "ExecutePipeline",
                                    "typeProperties": {
                                        "pipeline": {
                                            "referenceName": child_pipeline_name,
                                            "type": "PipelineReference",
                                        },
                                        "waitOnCompletion": True,
                                    },
                                },
                                {
                                    "name": "SetStatusSuccess",
                                    "type": "SetVariable",
                                    "typeProperties": {
                                        "variableName": "ExecutionStatus",
                                        "value": "PROCESSED_SUCCESSFULLY",
                                    },
                                },
                            ],
                            "ifFalseActivities": [
                                {
                                    "name": "SetStatusSkipped",
                                    "type": "SetVariable",
                                    "typeProperties": {
                                        "variableName": "ExecutionStatus",
                                        "value": "SKIPPED_NO_RECORDS",
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "name": "SendFailureAlert",
                        "type": "WebActivity",
                        "dependsOn": [
                            {
                                "activity": "CheckNewRecordsCount",
                                "dependencyConditions": ["Failed"],
                            }
                        ],
                        "typeProperties": {
                            "url": "https://prod-00.eastus.logic.azure.com/workflows/alert",
                            "method": "POST",
                            "headers": {"Content-Type": "application/json"},
                            "body": {
                                "pipeline": "@pipeline().Pipeline",
                                "error": "@activity('CheckNewRecordsCount').error.message",
                            },
                        },
                    },
                ],
            }
        }

    def build_switch_routing_pipeline_spec(
        self,
        pipeline_name: str,
    ) -> Dict[str, Any]:
        """
        Build pipeline with Switch Activity routing processing based on target environment or file format.

        Args:
            pipeline_name: Pipeline name

        Returns:
            Pipeline specification dict
        """
        return {
            "properties": {
                "description": "Multi-branch routing pipeline using Switch activity",
                "parameters": {
                    "DataFormat": {"type": "String", "defaultValue": "CSV"},
                },
                "activities": [
                    {
                        "name": "RouteByFormat",
                        "type": "Switch",
                        "dependsOn": [],
                        "typeProperties": {
                            "on": {
                                "value": "@pipeline().parameters.DataFormat",
                                "type": "Expression",
                            },
                            "cases": [
                                {
                                    "value": "CSV",
                                    "activities": [
                                        {
                                            "name": "ProcessCSV",
                                            "type": "SetVariable",
                                            "typeProperties": {
                                                "variableName": "ExecutionStatus",
                                                "value": "HANDLED_CSV",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "value": "PARQUET",
                                    "activities": [
                                        {
                                            "name": "ProcessParquet",
                                            "type": "SetVariable",
                                            "typeProperties": {
                                                "variableName": "ExecutionStatus",
                                                "value": "HANDLED_PARQUET",
                                            },
                                        }
                                    ],
                                },
                            ],
                            "defaultActivities": [
                                {
                                    "name": "ProcessDefaultJson",
                                    "type": "SetVariable",
                                    "typeProperties": {
                                        "variableName": "ExecutionStatus",
                                        "value": "HANDLED_DEFAULT",
                                    },
                                }
                            ],
                        },
                    }
                ],
                "variables": {
                    "ExecutionStatus": {"type": "String"},
                },
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
        logger.info("Deploying Conditional Pipeline: %s to %s/%s", pipeline_name, resource_group, factory_name)

        if self.client.config.mock_mode:
            logger.info("Mock mode: Conditional Pipeline %s deployed successfully", pipeline_name)
            return {"name": pipeline_name, "id": f"mock-cond-id-{pipeline_name}", "status": "Deployed"}

        adf = self.client.get_management_client()
        result = adf.pipelines.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            pipeline_name=pipeline_name,
            pipeline=pipeline_spec,
        )
        return {"name": result.name, "id": result.id}
