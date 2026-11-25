"""
Module for defining and orchestrating steps on Amazon EMR clusters.
Provides utilities to configure Spark, Hive, and bash shell steps, add them to EMR, and monitor progress.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EMRSteps")


class EMRStepOrchestrator:
    """
    Orchestrates execution of steps (Spark, Hive, Shell Scripts) on active AWS EMR clusters.
    """

    def __init__(self, emr_client: Optional[Any] = None, region_name: str = "us-east-1"):
        self.emr_client = emr_client or boto3.client("emr", region_name=region_name)

    @staticmethod
    def build_spark_step(
        name: str,
        script_uri: str,
        script_args: List[str],
        spark_submit_options: Optional[List[str]] = None,
        action_on_failure: str = "CONTINUE"
    ) -> Dict[str, Any]:
        """
        Builds a standard PySpark submit step configuration.
        """
        if not script_uri.startswith("s3://"):
            raise ValueError("Script URI must be stored in S3 (s3://...)")

        # Command runner jar is the standard entry point for EMR steps
        jar_path = "command-runner.jar"
        
        args = ["spark-submit"]
        if spark_submit_options:
            args.extend(spark_submit_options)
            
        args.append(script_uri)
        args.extend(script_args)

        return {
            "Name": name,
            "ActionOnFailure": action_on_failure,
            "HadoopJarStep": {
                "Jar": jar_path,
                "Args": args
            }
        }

    @staticmethod
    def build_hive_step(
        name: str,
        hive_script_uri: str,
        query_variables: Optional[Dict[str, str]] = None,
        action_on_failure: str = "CONTINUE"
    ) -> Dict[str, Any]:
        """
        Builds a Hive step config using script runner to execute custom HQL.
        """
        if not hive_script_uri.startswith("s3://"):
            raise ValueError("Hive script URI must be stored in S3 (s3://...)")

        jar_path = "command-runner.jar"
        args = ["hive-script", "--run-hive-script", "--args", "-f", hive_script_uri]
        
        if query_variables:
            for key, val in query_variables.items():
                args.extend(["-d", f"{key}={val}"])

        return {
            "Name": name,
            "ActionOnFailure": action_on_failure,
            "HadoopJarStep": {
                "Jar": jar_path,
                "Args": args
            }
        }

    @staticmethod
    def build_shell_step(
        name: str,
        script_uri: str,
        script_args: Optional[List[str]] = None,
        action_on_failure: str = "CONTINUE"
    ) -> Dict[str, Any]:
        """
        Builds a generic bash shell script execution step.
        """
        if not script_uri.startswith("s3://"):
            raise ValueError("Shell script URI must be stored in S3 (s3://...)")

        jar_path = "s3://us-east-1.elasticmapreduce/libs/script-runner/script-runner.jar"
        args = [script_uri]
        if script_args:
            args.extend(script_args)

        return {
            "Name": name,
            "ActionOnFailure": action_on_failure,
            "HadoopJarStep": {
                "Jar": jar_path,
                "Args": args
            }
        }

    def add_steps_to_cluster(self, cluster_id: str, steps: List[Dict[str, Any]]) -> List[str]:
        """
        Submits steps to a running EMR cluster.
        
        :return: List of Step IDs returned by AWS EMR.
        """
        logger.info("Submitting %d steps to EMR cluster %s...", len(steps), cluster_id)
        try:
            response = self.emr_client.add_job_flow_steps(
                JobFlowId=cluster_id,
                Steps=steps
            )
            step_ids = response["StepIds"]
            logger.info("Steps submitted successfully. IDs: %s", step_ids)
            return step_ids
        except ClientError as ce:
            logger.error("Failed to submit steps: %s", ce.response["Error"]["Message"])
            raise

    def get_step_status(self, cluster_id: str, step_id: str) -> Dict[str, Any]:
        """
        Retrieves the execution status details of a specific EMR step.
        """
        try:
            response = self.emr_client.describe_step(ClusterId=cluster_id, StepId=step_id)
            return response["Step"]["Status"]
        except ClientError as ce:
            logger.error("Failed to describe step %s: %s", step_id, ce.response["Error"]["Message"])
            raise

    def wait_for_step_completion(self, cluster_id: str, step_id: str, poll_interval: int = 15, max_wait_seconds: int = 1800) -> str:
        """
        Blocks execution until the step transitions to COMPLETED, FAILED, or CANCELLED.
        """
        logger.info("Waiting for step %s on cluster %s to finish...", step_id, cluster_id)
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            status = self.get_step_status(cluster_id, step_id)
            state = status["State"]
            
            logger.info("Step %s state: %s", step_id, state)
            
            if state == "COMPLETED":
                logger.info("Step %s completed successfully.", step_id)
                return state
            elif state in ["FAILED", "CANCELLED"]:
                reason = status.get("FailureDetails", {}).get("Reason", "No detail provided")
                log_file = status.get("FailureDetails", {}).get("LogFile", "No log file")
                logger.error("Step %s finished with state %s. Reason: %s. Log: %s", step_id, state, reason, log_file)
                return state
                
            time.sleep(poll_interval)
            
        raise TimeoutError(f"Step {step_id} did not finish within {max_wait_seconds} seconds.")
