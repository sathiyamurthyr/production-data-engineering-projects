import time
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

logger = logging.getLogger("glue_workflows")

class GlueWorkflowManager:
    """
    Manages AWS Glue Workflows to orchestrate ETL pipelines, triggers, and crawlers.
    """
    def __init__(self, region_name: str = "us-east-1"):
        try:
            self.client = boto3.client("glue", region_name=region_name)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Boto3 client initialization failed ({e}). Using mock client for local execution.")
            self.client = MockGlueWorkflowClient()
            self.is_mock = True

    def create_workflow(self, workflow_name: str, description: str = "") -> bool:
        """Creates an orchestration workflow container in AWS Glue."""
        try:
            self.client.create_workflow(
                Name=workflow_name,
                Description=description
            )
            logger.info(f"Glue Workflow '{workflow_name}' created successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Workflow '{workflow_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating Glue Workflow '{workflow_name}': {e}")
                raise e

    def start_workflow_run(self, workflow_name: str) -> Optional[str]:
        """Starts execution of a Glue Workflow, returning the RunId."""
        try:
            response = self.client.start_workflow_run(Name=workflow_name)
            run_id = response.get("RunId")
            logger.info(f"Glue Workflow '{workflow_name}' execution started. RunId: {run_id}")
            return run_id
        except ClientError as e:
            logger.error(f"Error starting execution for Glue Workflow '{workflow_name}': {e}")
            raise e

    def get_workflow_run_status(self, workflow_name: str, run_id: str) -> Dict[str, Any]:
        """
        Retrieves the execution status of a workflow run, including overall state
        and graph node status (crawlers, jobs, triggers).
        """
        try:
            response = self.client.get_workflow_run(Name=workflow_name, RunId=run_id, IncludeGraph=True)
            run_details = response.get("Run", {})
            
            # Simple summarization of graph states
            nodes_status = {}
            graph = run_details.get("Graph", {})
            for node in graph.get("Nodes", []):
                node_name = node.get("Name")
                node_type = node.get("Type") # JOB, CRAWLER, TRIGGER
                
                # Check execution detail states if present
                job_details = node.get("JobDetails", {})
                crawler_details = node.get("CrawlerDetails", {})
                trigger_details = node.get("TriggerDetails", {})
                
                status = "PENDING"
                if job_details.get("JobRuns"):
                    status = job_details["JobRuns"][0].get("JobRunState")
                elif crawler_details.get("CrawlRuns"):
                    status = crawler_details["CrawlRuns"][0].get("CrawlState")
                elif trigger_details.get("Trigger"):
                    status = trigger_details["Trigger"].get("State")

                nodes_status[node_name] = {
                    "Type": node_type,
                    "Status": status
                }

            return {
                "WorkflowName": workflow_name,
                "RunId": run_id,
                "WorkflowState": run_details.get("Status"), # RUNNING, COMPLETED, STOPPED, ERROR
                "StartedOn": run_details.get("StartedOn"),
                "CompletedOn": run_details.get("CompletedOn"),
                "Nodes": nodes_status
            }
        except ClientError as e:
            logger.error(f"Error getting run status for workflow '{workflow_name}' (RunId: {run_id}): {e}")
            raise e

    def wait_for_workflow_run(self, workflow_name: str, run_id: str, poll_interval: int = 15, timeout: int = 600) -> bool:
        """
        Polls the workflow run until it reaches a terminal status (COMPLETED, ERROR, STOPPED).
        """
        logger.info(f"Monitoring Workflow '{workflow_name}' run ID {run_id}. Polling every {poll_interval}s.")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_info = self.get_workflow_run_status(workflow_name, run_id)
            state = status_info.get("WorkflowState")
            logger.info(f"Workflow State: {state}")
            
            if state in ["COMPLETED", "STOPPED", "ERROR"]:
                if state == "COMPLETED":
                    logger.info("Workflow execution completed successfully.")
                    return True
                else:
                    logger.error(f"Workflow execution ended with state: {state}")
                    return False
            
            time.sleep(poll_interval)
            
        logger.error("Timeout reached waiting for Glue Workflow execution to finish.")
        return False

    def delete_workflow(self, workflow_name: str) -> bool:
        """Deletes a Glue Workflow container."""
        try:
            self.client.delete_workflow(Name=workflow_name)
            logger.info(f"Glue Workflow '{workflow_name}' deleted successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Workflow '{workflow_name}' already deleted or does not exist.")
                return True
            else:
                logger.error(f"Error deleting Glue Workflow '{workflow_name}': {e}")
                raise e


class MockGlueWorkflowClient:
    """Mock implementation of boto3 Glue Workflow operations for local runs and offline unit tests."""
    def __init__(self):
        self.workflows = {}
        self.runs = {}

    def create_workflow(self, Name: str, Description: str = "", **kwargs):
        if Name in self.workflows:
            raise ClientError({"Error": {"Code": "AlreadyExistsException", "Message": "Workflow already exists"}}, "create_workflow")
        self.workflows[Name] = {
            "Name": Name,
            "Description": Description,
            "DefaultRunProperties": {}
        }
        return {}

    def start_workflow_run(self, Name: str) -> Dict[str, str]:
        if Name not in self.workflows:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Workflow not found"}}, "start_workflow_run")
        run_id = f"wfr_{int(time.time())}"
        self.runs[run_id] = {
            "Status": "COMPLETED", # Instant completion for mock runs
            "StartedOn": time.time(),
            "CompletedOn": time.time(),
            "Graph": {
                "Nodes": [
                    {
                        "Name": "mock-crawl-node",
                        "Type": "CRAWLER",
                        "CrawlerDetails": {"CrawlRuns": [{"CrawlState": "SUCCEEDED"}]}
                    },
                    {
                        "Name": "mock-etl-node",
                        "Type": "JOB",
                        "JobDetails": {"JobRuns": [{"JobRunState": "SUCCEEDED"}]}
                    }
                ]
            }
        }
        return {"RunId": run_id}

    def get_workflow_run(self, Name: str, RunId: str, **kwargs) -> Dict[str, Any]:
        if RunId not in self.runs:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Workflow run not found"}}, "get_workflow_run")
        return {"Run": self.runs[RunId]}

    def delete_workflow(self, Name: str):
        if Name not in self.workflows:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Workflow not found"}}, "delete_workflow")
        del self.workflows[Name]
        return {}
