"""
mapping_dataflow_pipeline.py - Azure Data Factory Mapping Data Flow Pipeline Manager
======================================================================================
Production-grade Mapping Data Flow transformation pipeline creation and deployment.

Explanation:
    Mapping Data Flows execute visually designed data transformation logic compiled into Spark code
    running on managed Azure Databricks/Spark clusters managed by ADF Integration Runtime.
    Transformations include:
    - Filter (Row-level expression filtering)
    - Derived Column (Expression-based calculated columns)
    - Join (Inner, Left Outer, Right Outer, Full Outer, Cross joins)
    - Aggregate (Group-by aggregations with sum, avg, max, min)
    - Select (Column aliasing and dropping)
    - Sink (Target write with partition partitioning and schema validation)

Business Use Case:
    Complex ETL transformations (SCD Type 1/2, data cleansing, aggregations, deduplication)
    without writing custom PySpark code or managing Databricks clusters directly.

Production Example:
    mgr = MappingDataFlowPipelineManager(adf_client)
    dataflow_spec = mgr.build_sales_transformation_dataflow("DF_Sales_Cleansing")
    mgr.create_or_update_dataflow("my-rg", "my-adf", "DF_Sales_Cleansing", dataflow_spec)

Interview Questions:
    Q: What compute infrastructure powers Mapping Data Flows in ADF?
    A: ADF provisions short-lived (ephemeral) Azure Databricks Spark clusters automatically
       based on the Integration Runtime configuration (compute type and core count).

    Q: How do you optimize Mapping Data Flow performance?
    A: 1. Set Time-To-Live (TTL) on Integration Runtime to avoid cluster spin-up cold starts.
       2. Use Broadcast Joins for small dimension tables.
       3. Repartition data appropriately (Hash/RoundRobin) to prevent data skew.
"""

import logging, uuid
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class MappingDataFlowPipelineManager:
    """
    Manager for creating, configuring, and deploying ADF Mapping Data Flow pipelines.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def build_sales_transformation_dataflow_spec(
        self,
        dataflow_name: str,
        source_dataset_name: str = "ParquetSourceDS",
        sink_dataset_name: str = "ParquetSinkDS",
    ) -> Dict[str, Any]:
        """
        Build JSON specification for a Mapping Data Flow transformation graph:
        Source -> Filter (valid amount) -> DerivedColumn (tax calculation) -> Aggregate (daily totals) -> Sink.

        Args:
            dataflow_name: Data Flow name
            source_dataset_name: Source dataset reference
            sink_dataset_name: Sink dataset reference

        Returns:
            Data Flow resource payload dict
        """
        script_text = (
            f"source(output(\n"
            f"    order_id as string,\n"
            f"    customer_id as string,\n"
            f"    order_date as date,\n"
            f"    amount as double,\n"
            f"    status as string\n"
            f"), allowSchemaDrift: true, validateSchema: false, isIsolatedAttribute: false) ~> RawSalesSource\n"
            f"RawSalesSource filter(amount > 0.0 && status == 'COMPLETED') ~> FilterValidSales\n"
            f"FilterValidSales derive(\n"
            f"    tax_amount = round(amount * 0.08, 2),\n"
            f"    total_amount = round(amount * 1.08, 2),\n"
            f"    ingested_at = currentTimestamp()\n"
            f") ~> AddCalculatedColumns\n"
            f"AddCalculatedColumns aggregate(\n"
            f"    groupBy(order_date),\n"
            f"    daily_sales = sum(total_amount),\n"
            f"    daily_tax = sum(tax_amount),\n"
            f"    total_orders = count(order_id)\n"
            f") ~> AggregateDailyTotals\n"
            f"AggregateDailyTotals sink(\n"
            f"    allowSchemaDrift: true,\n"
            f"    validateSchema: false,\n"
            f"    partitionBy('hash', 4, order_date)\n"
            f") ~> CuratedGoldSink"
        )

        return {
            "properties": {
                "description": "Mapping Data Flow pipeline for cleansing, calculating tax, and aggregating daily sales",
                "sources": [
                    {
                        "name": "RawSalesSource",
                        "dataset": {
                            "referenceName": source_dataset_name,
                            "type": "DatasetReference",
                        },
                    }
                ],
                "sinks": [
                    {
                        "name": "CuratedGoldSink",
                        "dataset": {
                            "referenceName": sink_dataset_name,
                            "type": "DatasetReference",
                        },
                    }
                ],
                "transformations": [],
                "scriptLines": script_text.split("\n"),
            }
        }

    def build_dataflow_pipeline_activity_spec(
        self,
        pipeline_name: str,
        dataflow_name: str,
        integration_runtime_name: str = "AutoResolveIntegrationRuntime",
        compute_type: str = "General",
        core_count: int = 8,
    ) -> Dict[str, Any]:
        """
        Build Pipeline specification wrapping a Mapping Data Flow activity.

        Args:
            pipeline_name: Pipeline name
            dataflow_name: Mapping Data Flow name to invoke
            integration_runtime_name: IR name
            compute_type: 'General', 'MemoryOptimized', or 'ComputeOptimized'
            core_count: Spark cluster cores (8, 16, 32, 64, 128, 256)

        Returns:
            Pipeline payload dict
        """
        return {
            "properties": {
                "description": f"Pipeline executing Mapping Data Flow activity: {dataflow_name}",
                "activities": [
                    {
                        "name": f"Execute_{dataflow_name}",
                        "type": "ExecuteDataFlow",
                        "dependsOn": [],
                        "policy": {
                            "timeout": "0.02:00:00",
                            "retry": 1,
                            "retryIntervalInSeconds": 60,
                        },
                        "typeProperties": {
                            "dataflow": {
                                "referenceName": dataflow_name,
                                "type": "DataFlowReference",
                            },
                            "compute": {
                                "computeType": compute_type,
                                "coreCount": core_count,
                            },
                            "integrationRuntime": {
                                "referenceName": integration_runtime_name,
                                "type": "IntegrationRuntimeReference",
                            },
                            "traceLevel": "Fine",
                        },
                    }
                ],
            }
        }

    def create_or_update_dataflow(
        self,
        resource_group: str,
        factory_name: str,
        dataflow_name: str,
        dataflow_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deploy Mapping Data Flow definition to ADF.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            dataflow_name: Data Flow name
            dataflow_spec: Data Flow payload

        Returns:
            Created Data Flow metadata
        """
        logger.info("Deploying Data Flow: %s to %s/%s", dataflow_name, resource_group, factory_name)

        if self.client.config.mock_mode:
            logger.info("Mock mode: Data Flow %s deployed successfully", dataflow_name)
            return {"name": dataflow_name, "id": f"mock-dataflow-id-{dataflow_name}", "status": "Deployed"}

        adf = self.client.get_management_client()
        result = adf.data_flows.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            data_flow_name=dataflow_name,
            data_flow=dataflow_spec,
        )
        return {"name": result.name, "id": result.id}

    def trigger_dataflow_pipeline(
        self,
        resource_group: str,
        factory_name: str,
        pipeline_name: str,
    ) -> str:
        """
        Trigger run of Data Flow Pipeline.

        Returns:
            Run ID string
        """
        if self.client.config.mock_mode:
            mock_id = f"run-df-{uuid.uuid4()}"
            logger.info("Mock mode: Data Flow pipeline run triggered ID %s", mock_id)
            return mock_id

        adf = self.client.get_management_client()
        run = adf.pipelines.create_run(
            resource_group_name=resource_group,
            factory_name=factory_name,
            pipeline_name=pipeline_name,
        )
        return run.run_id
