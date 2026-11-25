import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional

logger = logging.getLogger("glue_triggers")

class GlueTriggerManager:
    """
    Manages AWS Glue Job Triggers (On-Demand, Scheduled, Event-Driven/Conditional).
    """
    def __init__(self, region_name: str = "us-east-1"):
        try:
            self.client = boto3.client("glue", region_name=region_name)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Boto3 client initialization failed ({e}). Using mock client for local execution.")
            self.client = MockGlueTriggerClient()
            self.is_mock = True

    def create_ondemand_trigger(
        self,
        trigger_name: str,
        job_names: List[str],
        description: str = "On-demand trigger for executing Glue ETL jobs"
    ) -> bool:
        """Creates an on-demand trigger to execute one or more jobs."""
        actions = [{"JobName": job_name} for job_name in job_names]
        
        try:
            self.client.create_trigger(
                Name=trigger_name,
                Type="ON_DEMAND",
                Actions=actions,
                Description=description
            )
            logger.info(f"On-demand Glue Trigger '{trigger_name}' created successfully for jobs: {job_names}.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Trigger '{trigger_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating on-demand trigger '{trigger_name}': {e}")
                raise e

    def create_scheduled_trigger(
        self,
        trigger_name: str,
        job_names: List[str],
        cron_expression: str,
        description: str = "Scheduled cron trigger for executing Glue ETL jobs"
    ) -> bool:
        """
        Creates a scheduled trigger based on a cron expression.
        Example cron: "cron(0 12 * * ? *)" (Run every day at 12:00 PM UTC)
        """
        actions = [{"JobName": job_name} for job_name in job_names]
        
        try:
            self.client.create_trigger(
                Name=trigger_name,
                Type="SCHEDULED",
                Schedule=cron_expression,
                Actions=actions,
                Description=description,
                StartOnCreation=True
            )
            logger.info(f"Scheduled Glue Trigger '{trigger_name}' ({cron_expression}) created successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Trigger '{trigger_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating scheduled trigger '{trigger_name}': {e}")
                raise e

    def create_conditional_trigger(
        self,
        trigger_name: str,
        job_names: List[str],
        predicate_conditions: List[Dict[str, Any]],
        description: str = "Conditional/event-driven trigger for executing Glue ETL jobs"
    ) -> bool:
        """
        Creates a conditional/event-driven trigger. Starts the target jobs only when 
        predicate conditions are met (e.g., source job SUCCEEDED).
        
        Example predicate_conditions:
        [
            {
                "LogicalOperator": "EQUALS",
                "JobName": "source_raw_etl",
                "State": "SUCCEEDED"
            }
        ]
        """
        actions = [{"JobName": job_name} for job_name in job_names]
        
        # Build Glue Predicate structure
        conditions = []
        for cond in predicate_conditions:
            conditions.append({
                "LogicalOperator": cond.get("LogicalOperator", "EQUALS"),
                "JobName": cond.get("JobName"),
                "State": cond.get("State", "SUCCEEDED")
            })
            
        predicate = {
            "Logical": "AND",
            "Conditions": conditions
        }

        try:
            self.client.create_trigger(
                Name=trigger_name,
                Type="CONDITIONAL",
                Predicate=predicate,
                Actions=actions,
                Description=description,
                StartOnCreation=True
            )
            logger.info(f"Conditional Glue Trigger '{trigger_name}' created successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Trigger '{trigger_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating conditional trigger '{trigger_name}': {e}")
                raise e

    def start_trigger(self, trigger_name: str) -> bool:
        """Starts (activates) an inactive trigger."""
        try:
            self.client.start_trigger(Name=trigger_name)
            logger.info(f"Glue Trigger '{trigger_name}' activated successfully.")
            return True
        except ClientError as e:
            logger.error(f"Error starting Glue Trigger '{trigger_name}': {e}")
            raise e

    def stop_trigger(self, trigger_name: str) -> bool:
        """Stops (deactivates) an active trigger."""
        try:
            self.client.stop_trigger(Name=trigger_name)
            logger.info(f"Glue Trigger '{trigger_name}' deactivated successfully.")
            return True
        except ClientError as e:
            logger.error(f"Error stopping Glue Trigger '{trigger_name}': {e}")
            raise e

    def get_trigger(self, trigger_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a trigger."""
        try:
            response = self.client.get_trigger(Name=trigger_name)
            return response.get("Trigger")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Trigger '{trigger_name}' not found.")
                return None
            else:
                logger.error(f"Error getting Glue Trigger '{trigger_name}': {e}")
                raise e

    def delete_trigger(self, trigger_name: str) -> bool:
        """Deletes a trigger."""
        try:
            self.client.delete_trigger(Name=trigger_name)
            logger.info(f"Glue Trigger '{trigger_name}' deleted successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Trigger '{trigger_name}' already deleted or does not exist.")
                return True
            else:
                logger.error(f"Error deleting Glue Trigger '{trigger_name}': {e}")
                raise e


class MockGlueTriggerClient:
    """Mock implementation of boto3 Glue Trigger operations for local runs and offline unit tests."""
    def __init__(self):
        self.triggers = {}

    def create_trigger(self, Name: str, Type: str, Actions: List[Dict[str, Any]], **kwargs):
        if Name in self.triggers:
            raise ClientError({"Error": {"Code": "AlreadyExistsException", "Message": "Trigger already exists"}}, "create_trigger")
        
        state = "ACTIVATED" if Type in ["SCHEDULED", "CONDITIONAL"] else "DEACTIVATED"
        self.triggers[Name] = {
            "Name": Name,
            "Type": Type,
            "Actions": Actions,
            "State": state,
            "Schedule": kwargs.get("Schedule"),
            "Predicate": kwargs.get("Predicate"),
            "Description": kwargs.get("Description")
        }
        return {}

    def start_trigger(self, Name: str):
        if Name not in self.triggers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Trigger not found"}}, "start_trigger")
        self.triggers[Name]["State"] = "ACTIVATED"
        return {}

    def stop_trigger(self, Name: str):
        if Name not in self.triggers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Trigger not found"}}, "stop_trigger")
        self.triggers[Name]["State"] = "DEACTIVATED"
        return {}

    def get_trigger(self, Name: str) -> Dict[str, Any]:
        if Name not in self.triggers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Trigger not found"}}, "get_trigger")
        return {"Trigger": self.triggers[Name]}

    def delete_trigger(self, Name: str):
        if Name not in self.triggers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Trigger not found"}}, "delete_trigger")
        del self.triggers[Name]
        return {}
