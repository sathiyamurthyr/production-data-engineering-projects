import time
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

logger = logging.getLogger("glue_crawlers")

class GlueCrawlerManager:
    """
    Manages AWS Glue Crawlers including creation, start, stop, deletion, and status monitoring.
    """
    def __init__(self, region_name: str = "us-east-1"):
        try:
            self.client = boto3.client("glue", region_name=region_name)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Boto3 client initialization failed ({e}). Using mock client for local execution.")
            self.client = MockGlueCrawlerClient()
            self.is_mock = True

    def create_crawler(
        self,
        crawler_name: str,
        role_arn: str,
        database_name: str,
        s3_target_path: str,
        schedule: Optional[str] = None,
        table_prefix: str = ""
    ) -> bool:
        """
        Creates a new Glue Crawler.
        """
        targets = {
            "S3Targets": [
                {
                    "Path": s3_target_path
                }
            ]
        }
        
        crawler_input = {
            "Name": crawler_name,
            "Role": role_arn,
            "DatabaseName": database_name,
            "Targets": targets,
            "TablePrefix": table_prefix,
            "SchemaChangePolicy": {
                "UpdateBehavior": "UPDATE_IN_DATABASE",
                "DeleteBehavior": "DEPRECATE_IN_DATABASE"
            }
        }
        
        if schedule:
            crawler_input["Schedule"] = {"ScheduleExpression": schedule}

        try:
            self.client.create_crawler(**crawler_input)
            logger.info(f"Glue Crawler '{crawler_name}' created successfully referencing S3 path '{s3_target_path}'.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Crawler '{crawler_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating Glue Crawler '{crawler_name}': {e}")
                raise e

    def start_crawler(self, crawler_name: str) -> bool:
        """Starts a Glue Crawler."""
        try:
            self.client.start_crawler(Name=crawler_name)
            logger.info(f"Glue Crawler '{crawler_name}' started running.")
            return True
        except ClientError as e:
            logger.error(f"Error starting Glue Crawler '{crawler_name}': {e}")
            raise e

    def stop_crawler(self, crawler_name: str) -> bool:
        """Stops a Glue Crawler."""
        try:
            self.client.stop_crawler(Name=crawler_name)
            logger.info(f"Glue Crawler '{crawler_name}' stopping command issued.")
            return True
        except ClientError as e:
            logger.error(f"Error stopping Glue Crawler '{crawler_name}': {e}")
            raise e

    def get_crawler_status(self, crawler_name: str) -> Dict[str, Any]:
        """
        Retrieves current state and status metrics of the Crawler.
        Returns:
            Dict containing Status ('READY', 'RUNNING', 'STOPPING') and execution details.
        """
        try:
            response = self.client.get_crawler(Name=crawler_name)
            crawler_info = response.get("Crawler", {})
            return {
                "Name": crawler_info.get("Name"),
                "State": crawler_info.get("State"), # READY, RUNNING, STOPPING
                "LastCrawlStatus": crawler_info.get("LastCrawl", {}).get("Status"),
                "CrawlTimeSeconds": crawler_info.get("LastCrawl", {}).get("Message")
            }
        except ClientError as e:
            logger.error(f"Error retrieving Crawler status for '{crawler_name}': {e}")
            raise e

    def wait_for_crawler(self, crawler_name: str, poll_interval_seconds: int = 10, timeout_seconds: int = 300) -> bool:
        """
        Blocks and polls until the crawler transitions back to the 'READY' state.
        """
        logger.info(f"Monitoring Crawler '{crawler_name}' execution. Polling every {poll_interval_seconds}s.")
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            status = self.get_crawler_status(crawler_name)
            state = status.get("State")
            logger.info(f"Crawler state: {state}")
            
            if state == "READY":
                last_status = status.get("LastCrawlStatus")
                logger.info(f"Crawler finished. Final execution status: {last_status}")
                return last_status == "SUCCEEDED" or last_status is None
            
            time.sleep(poll_interval_seconds)
            
        logger.error(f"Timeout reached waiting for Crawler '{crawler_name}' to finish.")
        return False

    def delete_crawler(self, crawler_name: str) -> bool:
        """Deletes a Glue Crawler."""
        try:
            self.client.delete_crawler(Name=crawler_name)
            logger.info(f"Glue Crawler '{crawler_name}' deleted successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Crawler '{crawler_name}' not found or already deleted.")
                return True
            else:
                logger.error(f"Error deleting Glue Crawler '{crawler_name}': {e}")
                raise e


class MockGlueCrawlerClient:
    """Mock implementation of boto3 Glue Crawler operations for local runs and offline unit tests."""
    def __init__(self):
        self.crawlers = {}

    def create_crawler(self, Name: str, Role: str, DatabaseName: str, Targets: Dict[str, Any], **kwargs):
        if Name in self.crawlers:
            raise ClientError({"Error": {"Code": "AlreadyExistsException", "Message": "Crawler already exists"}}, "create_crawler")
        self.crawlers[Name] = {
            "Name": Name,
            "Role": Role,
            "DatabaseName": DatabaseName,
            "Targets": Targets,
            "State": "READY",
            "LastCrawl": {"Status": None, "Message": "Never run"}
        }
        return {}

    def get_crawler(self, Name: str) -> Dict[str, Any]:
        if Name not in self.crawlers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Crawler not found"}}, "get_crawler")
        return {"Crawler": self.crawlers[Name]}

    def start_crawler(self, Name: str):
        if Name not in self.crawlers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Crawler not found"}}, "start_crawler")
        crawler = self.crawlers[Name]
        if crawler["State"] == "RUNNING":
            raise ClientError({"Error": {"Code": "CrawlerRunningException", "Message": "Crawler is already running"}}, "start_crawler")
        crawler["State"] = "RUNNING"
        # Simulate state transitions during get_crawler calls
        crawler["LastCrawl"] = {"Status": "SUCCEEDED", "Message": "15"}
        # For mock simplicity, we will immediately set status back to READY upon subsequent checks
        # but let's do a state mutation helper
        return {}

    def stop_crawler(self, Name: str):
        if Name not in self.crawlers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Crawler not found"}}, "stop_crawler")
        crawler = self.crawlers[Name]
        crawler["State"] = "READY"
        crawler["LastCrawl"]["Status"] = "CANCELLED"
        return {}

    def delete_crawler(self, Name: str):
        if Name not in self.crawlers:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Crawler not found"}}, "delete_crawler")
        del self.crawlers[Name]
        return {}
