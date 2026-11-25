"""
trigger_management.py - Azure Data Factory Trigger Management
================================================================
Production-grade deployment and lifecycle management for ADF Triggers.

Explanation:
    Triggers determine when pipeline runs are automatically executed. ADF supports:
    1. Schedule Trigger: Wall-clock time schedule (e.g. Every day at 02:00 UTC).
    2. Tumbling Window Trigger: Periodic, contiguous time slices with dependency management,
       retry policies, and backfill capabilities. Best for historical state processing.
    3. Storage Event Trigger: Event-driven execution reacting to Blob Created / Blob Deleted events
       in Azure Event Grid / Blob Storage.

Business Use Case:
    Production pipelines run on automated triggers. Event-driven triggers ingest data instantly
    when a file arrives in storage, while Tumbling Window triggers guarantee hourly/daily partition
    processing in sequential order with backfill capabilities for missed windows.

Production Example:
    trigger_mgr = TriggerManager(adf_client)
    trigger_mgr.create_schedule_trigger(
        resource_group="my-rg", factory_name="my-adf",
        trigger_name="TR_Daily_Sales_0200", pipeline_name="PL_Ingest_Sales_SQL",
        recurrence_frequency="Day", recurrence_interval=1, start_time="2026-01-01T02:00:00Z"
    )
    trigger_mgr.start_trigger("my-rg", "my-adf", "TR_Daily_Sales_0200")

Interview Questions:
    Q: What is the key advantage of Tumbling Window Triggers over Schedule Triggers?
    A: Tumbling Window triggers are stateful, contiguous, non-overlapping time windows that support
       self-dependencies (Window N depends on Window N-1 succeeding) and automated backfill for past windows.
       Schedule triggers are stateless wall-clock timers that do not track historical window state.

    Q: How does a Storage Event Trigger work in ADF?
    A: It integrates with Azure Event Grid under the hood. When a blob is created or deleted in a specified
       container/folder path matching a pattern (e.g., `*.csv`), Event Grid fires an event that ADF captures to trigger the pipeline.
"""

import logging
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Manager for creating, starting, stopping, and managing ADF Triggers.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def create_schedule_trigger(
        self,
        resource_group: str,
        factory_name: str,
        trigger_name: str,
        pipeline_name: str,
        recurrence_frequency: str = "Day",
        recurrence_interval: int = 1,
        start_time: str = "2026-01-01T00:00:00Z",
        time_zone: str = "UTC",
        pipeline_parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Schedule Trigger.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            trigger_name: Trigger name
            pipeline_name: Pipeline name to trigger
            recurrence_frequency: 'Minute', 'Hour', 'Day', 'Week', 'Month'
            recurrence_interval: Interval step (e.g. every 1 Day, every 15 Minutes)
            start_time: ISO 8601 start timestamp
            time_zone: Timezone string (default 'UTC')
            pipeline_parameters: Runtime parameters to pass to pipeline

        Returns:
            Created Trigger metadata
        """
        logger.info("Creating Schedule Trigger: %s for Pipeline: %s", trigger_name, pipeline_name)

        params = pipeline_parameters or {}

        payload = {
            "properties": {
                "type": "ScheduleTrigger",
                "typeProperties": {
                    "recurrence": {
                        "frequency": recurrence_frequency,
                        "interval": recurrence_interval,
                        "startTime": start_time,
                        "timeZone": time_zone,
                    }
                },
                "pipelines": [
                    {
                        "pipelineReference": {
                            "referenceName": pipeline_name,
                            "type": "PipelineReference",
                        },
                        "parameters": params,
                    }
                ],
                "description": f"Schedule trigger recurring every {recurrence_interval} {recurrence_frequency}(s)",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: Schedule Trigger %s created", trigger_name)
            return {"name": trigger_name, "type": "ScheduleTrigger", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.triggers.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            trigger_name=trigger_name,
            trigger=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_tumbling_window_trigger(
        self,
        resource_group: str,
        factory_name: str,
        trigger_name: str,
        pipeline_name: str,
        frequency: str = "Hour",
        interval: int = 1,
        start_time: str = "2026-01-01T00:00:00Z",
        max_concurrency: int = 3,
        delay_in_seconds: int = 0,
        retry_policy_count: int = 3,
        retry_policy_interval_in_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Create a Tumbling Window Trigger with backfill support and retry policies.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            trigger_name: Trigger name
            pipeline_name: Target pipeline name
            frequency: 'Hour' or 'Minute'
            interval: Window size interval
            start_time: ISO 8601 window start time
            max_concurrency: Concurrent active window runs (1 to 50)
            delay_in_seconds: Execution delay after window end
            retry_policy_count: Automatic retry count on failure
            retry_policy_interval_in_seconds: Seconds between retries

        Returns:
            Created Trigger metadata
        """
        logger.info("Creating Tumbling Window Trigger: %s for Pipeline: %s", trigger_name, pipeline_name)

        payload = {
            "properties": {
                "type": "TumblingWindowTrigger",
                "typeProperties": {
                    "frequency": frequency,
                    "interval": interval,
                    "startTime": start_time,
                    "maxConcurrency": max_concurrency,
                    "delay": delay_in_seconds,
                    "retryPolicy": {
                        "count": retry_policy_count,
                        "intervalInSeconds": retry_policy_interval_in_seconds,
                    },
                },
                "pipeline": {
                    "pipelineReference": {
                        "referenceName": pipeline_name,
                        "type": "PipelineReference",
                    },
                    "parameters": {
                        "WindowStart": "@trigger().outputs.windowStartTime",
                        "WindowEnd": "@trigger().outputs.windowEndTime",
                    },
                },
                "description": "Tumbling window trigger with window parameters and automated backfill",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: Tumbling Window Trigger %s created", trigger_name)
            return {"name": trigger_name, "type": "TumblingWindowTrigger", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.triggers.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            trigger_name=trigger_name,
            trigger=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_storage_event_trigger(
        self,
        resource_group: str,
        factory_name: str,
        trigger_name: str,
        pipeline_name: str,
        storage_account_id: str,
        blob_path_begins_with: str = "raw/incoming/",
        blob_path_ends_with: str = ".csv",
        events: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Storage Event Trigger for event-driven file processing.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            trigger_name: Trigger name
            pipeline_name: Target pipeline name
            storage_account_id: Azure Resource ID of Storage Account
            blob_path_begins_with: Blob path prefix filter
            blob_path_ends_with: Blob path suffix filter
            events: Trigger events list (default: ['Microsoft.Storage.BlobCreated'])

        Returns:
            Created Trigger metadata
        """
        logger.info("Creating Storage Event Trigger: %s (Prefix=%s)", trigger_name, blob_path_begins_with)

        event_types = events or ["Microsoft.Storage.BlobCreated"]

        payload = {
            "properties": {
                "type": "BlobEventsTrigger",
                "typeProperties": {
                    "blobPathBeginsWith": blob_path_begins_with,
                    "blobPathEndsWith": blob_path_ends_with,
                    "ignoreEmptyBlobs": True,
                    "scope": storage_account_id,
                    "events": event_types,
                },
                "pipelines": [
                    {
                        "pipelineReference": {
                            "referenceName": pipeline_name,
                            "type": "PipelineReference",
                        },
                        "parameters": {
                            "FolderPath": "@trigger().outputs.folderPath",
                            "FileName": "@trigger().outputs.fileName",
                        },
                    }
                ],
                "description": "Event-driven trigger reacting to storage blob creation",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: Storage Event Trigger %s created", trigger_name)
            return {"name": trigger_name, "type": "BlobEventsTrigger", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.triggers.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            trigger_name=trigger_name,
            trigger=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def start_trigger(self, resource_group: str, factory_name: str, trigger_name: str) -> None:
        """
        Start/Activate a deployed trigger.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            trigger_name: Trigger name
        """
        logger.info("Starting Trigger: %s in %s/%s", trigger_name, resource_group, factory_name)
        if not self.client.config.mock_mode:
            adf = self.client.get_management_client()
            poller = adf.triggers.begin_start(
                resource_group_name=resource_group,
                factory_name=factory_name,
                trigger_name=trigger_name,
            )
            poller.result()
        logger.info("Trigger %s started successfully", trigger_name)

    def stop_trigger(self, resource_group: str, factory_name: str, trigger_name: str) -> None:
        """
        Stop/Deactivate a trigger.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            trigger_name: Trigger name
        """
        logger.info("Stopping Trigger: %s in %s/%s", trigger_name, resource_group, factory_name)
        if not self.client.config.mock_mode:
            adf = self.client.get_management_client()
            poller = adf.triggers.begin_stop(
                resource_group_name=resource_group,
                factory_name=factory_name,
                trigger_name=trigger_name,
            )
            poller.result()
        logger.info("Trigger %s stopped successfully", trigger_name)
