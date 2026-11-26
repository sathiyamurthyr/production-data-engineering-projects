import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

logger = logging.getLogger("monitoring_glue")

class GlueJobMonitor:
    """
    Manages monitoring of AWS Glue Job runs, logging custom metrics to CloudWatch,
    and triggering alerts via Amazon SNS.
    """
    def __init__(self, region_name: str = "us-east-1"):
        try:
            self.glue_client = boto3.client("glue", region_name=region_name)
            self.cw_client = boto3.client("cloudwatch", region_name=region_name)
            self.sns_client = boto3.client("sns", region_name=region_name)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Boto3 clients initialization failed ({e}). Using mock clients for local execution.")
            self.glue_client = MockGlueClient()
            self.cw_client = MockCloudWatchClient()
            self.sns_client = MockSNSClient()
            self.is_mock = True

    def publish_job_metric(
        self,
        job_name: str,
        metric_name: str,
        value: float,
        unit: str = "Count",
        namespace: str = "AWSGlueDataEngineering"
    ) -> bool:
        """Publishes custom telemetry metrics to AWS CloudWatch."""
        try:
            self.cw_client.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Dimensions": [
                            {
                                "Name": "JobName",
                                "Value": job_name
                            }
                        ],
                        "Value": value,
                        "Unit": unit
                    }
                ]
            )
            logger.info(f"Published custom CloudWatch Metric: '{namespace}/{metric_name}' = {value} for job '{job_name}'.")
            return True
        except ClientError as e:
            logger.error(f"Error publishing metric to CloudWatch: {e}")
            raise e

    def send_sns_alert(self, topic_arn: str, subject: str, message: str) -> bool:
        """Publishes operational alerts to an Amazon SNS topic."""
        try:
            self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=message
            )
            logger.info(f"SNS notification sent successfully to topic '{topic_arn}'.")
            return True
        except ClientError as e:
            logger.error(f"Error sending SNS notification: {e}")
            raise e

    def get_job_run_details(self, job_name: str, run_id: str) -> Dict[str, Any]:
        """Fetches detailed execution status and run statistics of a Glue job run."""
        try:
            response = self.glue_client.get_job_run(JobName=job_name, RunId=run_id)
            run = response.get("JobRun", {})
            return {
                "JobName": run.get("JobName"),
                "RunId": run.get("Id"),
                "JobRunState": run.get("JobRunState"), # STARTING, RUNNING, STOPPING, STOPPED, SUCCEEDED, FAILED, TIMEOUT
                "ErrorMessage": run.get("ErrorMessage"),
                "ExecutionTime": run.get("ExecutionTime", 0), # in seconds
                "DPUSeconds": run.get("DPUSeconds"),
                "LogGroupName": run.get("LogGroupName")
            }
        except ClientError as e:
            logger.error(f"Error retrieving job run details for '{job_name}' run '{run_id}': {e}")
            raise e


class MockGlueClient:
    """Mock boto3 Glue client for job runs."""
    def __init__(self):
        self.runs = {
            "jr_mock12345": {
                "JobName": "ecommerce_sales_etl",
                "Id": "jr_mock12345",
                "JobRunState": "SUCCEEDED",
                "ErrorMessage": None,
                "ExecutionTime": 120,
                "DPUSeconds": 240,
                "LogGroupName": "/aws-glue/jobs/output"
            }
        }

    def get_job_run(self, JobName: str, RunId: str) -> Dict[str, Any]:
        if RunId not in self.runs:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Job run not found"}}, "get_job_run")
        return {"JobRun": self.runs[RunId]}


class MockCloudWatchClient:
    """Mock boto3 CloudWatch client for metric logs."""
    def put_metric_data(self, Namespace: str, MetricData: list):
        logger.info(f"Mock CloudWatch put_metric_data inside '{Namespace}': {MetricData}")
        return {}


class MockSNSClient:
    """Mock boto3 SNS client for alerts."""
    def publish(self, TopicArn: str, Subject: str, Message: str):
        logger.info(f"Mock SNS publish to topic '{TopicArn}':\nSubject: {Subject}\nMessage: {Message}")
        return {"MessageId": "mock-msg-uuid-12345"}
