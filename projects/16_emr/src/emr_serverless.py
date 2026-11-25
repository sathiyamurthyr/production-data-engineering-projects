"""
AWS EMR Serverless management and orchestration client.
Handles Serverless Application lifecycle, starting/stopping, job submission, and status polling.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EMRServerlessClient")


class EMRServerlessManager:
    """
    Manages EMR Serverless application environments and job executions via boto3 EMR-Serverless API.
    """

    def __init__(self, region_name: str = "us-east-1", aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None):
        try:
            self.client = boto3.client(
                "emr-serverless",
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            logger.info("EMR Serverless Client initialized in region %s", region_name)
        except Exception as e:
            logger.error("Failed to initialize EMR Serverless client: %s", str(e))
            raise

    def create_application(
        self,
        name: str,
        release_label: str = "emr-6.13.0",
        type: str = "SPARK",
        initial_capacity: Optional[Dict[str, Any]] = None,
        maximum_capacity: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Creates an EMR Serverless application environment.
        """
        logger.info("Creating EMR Serverless application '%s' of type '%s'...", name, type)
        try:
            params = {
                "name": name,
                "releaseLabel": release_label,
                "type": type,
            }
            if initial_capacity:
                params["initialCapacity"] = initial_capacity
            if maximum_capacity:
                params["maximumCapacity"] = maximum_capacity

            response = self.client.create_application(**params)
            app_id = response["applicationId"]
            logger.info("Application created successfully. ID: %s", app_id)
            return app_id
        except ClientError as ce:
            logger.error("Failed to create application: %s", ce.response["Error"]["Message"])
            raise

    def start_application(self, application_id: str) -> None:
        """
        Starts the EMR Serverless application so it can receive jobs.
        """
        logger.info("Starting application %s...", application_id)
        try:
            self.client.start_application(applicationId=application_id)
            # Wait for it to become STARTED
            self.wait_for_application_state(application_id, "STARTED")
        except ClientError as ce:
            logger.error("Failed to start application %s: %s", application_id, ce.response["Error"]["Message"])
            raise

    def stop_application(self, application_id: str) -> None:
        """
        Stops the application to avoid idle runtime costs.
        """
        logger.info("Stopping application %s...", application_id)
        try:
            self.client.stop_application(applicationId=application_id)
            self.wait_for_application_state(application_id, "STOPPED")
        except ClientError as ce:
            logger.error("Failed to stop application %s: %s", application_id, ce.response["Error"]["Message"])
            raise

    def delete_application(self, application_id: str) -> None:
        """
        Deletes the EMR Serverless application.
        """
        logger.info("Deleting application %s...", application_id)
        try:
            self.client.delete_application(applicationId=application_id)
            logger.info("Application %s deleted successfully.", application_id)
        except ClientError as ce:
            logger.error("Failed to delete application %s: %s", application_id, ce.response["Error"]["Message"])
            raise

    def get_application(self, application_id: str) -> Dict[str, Any]:
        """
        Retrieves details of the EMR Serverless application.
        """
        try:
            response = self.client.get_application(applicationId=application_id)
            return response["application"]
        except ClientError as ce:
            logger.error("Failed to get application %s: %s", application_id, ce.response["Error"]["Message"])
            raise

    def wait_for_application_state(self, application_id: str, target_state: str, poll_interval: int = 10, max_wait_seconds: int = 300) -> None:
        """
        Blocks until the EMR Serverless application reaches the target state.
        """
        logger.info("Waiting for application %s to reach state %s...", application_id, target_state)
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            app = self.get_application(application_id)
            state = app["state"]
            logger.info("Application state: %s", state)
            if state == target_state:
                logger.info("Application successfully reached state: %s", target_state)
                return
            time.sleep(poll_interval)
        raise TimeoutError(f"Application {application_id} did not reach {target_state} within {max_wait_seconds} seconds.")

    def start_job_run(
        self,
        application_id: str,
        execution_role_arn: str,
        entry_point: str,
        entry_point_arguments: List[str],
        spark_submit_parameters: Optional[str] = None,
        name: Optional[str] = None,
        s3_log_uri: Optional[str] = None
    ) -> str:
        """
        Submits a job run execution to an active EMR Serverless application.
        """
        logger.info("Submitting job to Serverless App %s...", application_id)
        try:
            job_driver = {
                "sparkSubmit": {
                    "entryPoint": entry_point,
                    "entryPointArguments": entry_point_arguments
                }
            }
            if spark_submit_parameters:
                job_driver["sparkSubmit"]["sparkSubmitParameters"] = spark_submit_parameters

            conf: Dict[str, Any] = {}
            if s3_log_uri:
                conf["monitoringConfiguration"] = {
                    "s3MonitoringConfiguration": {
                        "logUri": s3_log_uri
                    }
                }

            params: Dict[str, Any] = {
                "applicationId": application_id,
                "executionRoleArn": execution_role_arn,
                "jobDriver": job_driver
            }
            if name:
                params["name"] = name
            if conf:
                params["configurationOverrides"] = conf

            response = self.client.start_job_run(**params)
            job_run_id = response["jobRunId"]
            logger.info("Job submitted. Job Run ID: %s", job_run_id)
            return job_run_id

        except ClientError as ce:
            logger.error("Failed to start job run: %s", ce.response["Error"]["Message"])
            raise

    def get_job_run(self, application_id: str, job_run_id: str) -> Dict[str, Any]:
        """
        Retrieves status details of a specific job run.
        """
        try:
            response = self.client.get_job_run(applicationId=application_id, jobRunId=job_run_id)
            return response["jobRun"]
        except ClientError as ce:
            logger.error("Failed to get job run status: %s", ce.response["Error"]["Message"])
            raise

    def wait_for_job_run(self, application_id: str, job_run_id: str, poll_interval: int = 15, max_wait_seconds: int = 1800) -> str:
        """
        Blocks until the job run completes (SUCCESS, FAILED, CANCELLED).
        """
        logger.info("Waiting for job run %s to complete...", job_run_id)
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            job = self.get_job_run(application_id, job_run_id)
            state = job["state"]
            logger.info("Job run %s state: %s", job_run_id, state)

            if state == "SUCCESS":
                logger.info("Job run completed successfully.")
                return state
            elif state in ["FAILED", "CANCELLED"]:
                reason = job.get("stateDetails", "No reason provided")
                logger.error("Job run failed with state %s. Reason: %s", state, reason)
                return state

            time.sleep(poll_interval)
            
        raise TimeoutError(f"Job run {job_run_id} did not finish within {max_wait_seconds} seconds.")
