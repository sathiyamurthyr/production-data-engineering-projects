"""
EMR Client module for AWS EMR cluster lifecycle management.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EMRClient")


class EMRClusterManager:
    """
    Manages AWS EMR cluster provisioning, query, and termination lifecycle using boto3.
    """

    def __init__(self, region_name: str = "us-east-1", aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None):
        """
        Initializes the boto3 EMR client.
        """
        try:
            self.region_name = region_name
            self.emr_client = boto3.client(
                "emr",
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            logger.info("Successfully initialized EMR client in region %s", region_name)
        except Exception as e:
            logger.error("Failed to initialize EMR client: %s", str(e))
            raise

    def create_cluster(self, config: Dict[str, Any]) -> str:
        """
        Launches an EMR cluster with the provided configuration dictionary.
        
        :param config: Dictionary containing RunJobFlow parameters.
        :return: JobFlowId (Cluster ID) of the newly created cluster.
        """
        logger.info("Initiating EMR cluster creation...")
        try:
            # Basic validation of required EMR parameters
            required_keys = ["Name", "ReleaseLabel", "Instances", "ServiceRole", "JobFlowRole"]
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"Missing required configuration key: {key}")

            response = self.emr_client.run_job_flow(**config)
            cluster_id = response["JobFlowId"]
            logger.info("Successfully provisioned EMR cluster. Cluster ID: %s", cluster_id)
            return cluster_id

        except ClientError as ce:
            logger.error("AWS ClientError occurred during cluster creation: %s", ce.response["Error"]["Message"])
            raise
        except Exception as e:
            logger.error("Unexpected error during cluster creation: %s", str(e))
            raise

    def describe_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information about the specified EMR cluster.
        
        :param cluster_id: The ID of the EMR cluster.
        :return: A dictionary containing cluster details.
        """
        try:
            response = self.emr_client.describe_cluster(ClusterId=cluster_id)
            return response["Cluster"]
        except ClientError as ce:
            logger.error("Failed to describe cluster %s: %s", cluster_id, ce.response["Error"]["Message"])
            raise
        except Exception as e:
            logger.error("Unexpected error when describing cluster %s: %s", cluster_id, str(e))
            raise

    def get_cluster_status(self, cluster_id: str) -> str:
        """
        Gets the current state of the EMR cluster (e.g., STARTING, BOOTSTRAPPING, RUNNING, WAITING, TERMINATED).
        
        :param cluster_id: The ID of the EMR cluster.
        :return: State string.
        """
        details = self.describe_cluster(cluster_id)
        state = details["Status"]["State"]
        logger.info("Cluster %s state: %s", cluster_id, state)
        return state

    def terminate_cluster(self, cluster_id: str) -> None:
        """
        Terminates the specified EMR cluster.
        
        :param cluster_id: The ID of the EMR cluster to terminate.
        """
        logger.info("Terminating EMR cluster %s...", cluster_id)
        try:
            self.emr_client.terminate_job_flows(JobFlowIds=[cluster_id])
            logger.info("Termination request sent successfully for EMR cluster %s", cluster_id)
        except ClientError as ce:
            logger.error("Failed to terminate cluster %s: %s", cluster_id, ce.response["Error"]["Message"])
            raise
        except Exception as e:
            logger.error("Unexpected error during cluster termination %s: %s", cluster_id, str(e))
            raise

    def wait_for_cluster_state(self, cluster_id: str, target_states: List[str], poll_interval: int = 30, max_wait_seconds: int = 1200) -> str:
        """
        Blocks until the EMR cluster transitions into one of the target states or fails.
        
        :param cluster_id: The cluster ID to monitor.
        :param target_states: List of states to wait for (e.g. ['WAITING', 'RUNNING']).
        :param poll_interval: Polling frequency in seconds.
        :param max_wait_seconds: Time limit in seconds before raising timeout.
        :return: Final state of the cluster.
        """
        logger.info("Waiting for cluster %s to reach one of the states: %s", cluster_id, target_states)
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            state = self.get_cluster_status(cluster_id)
            if state in target_states:
                logger.info("Cluster %s successfully reached target state %s", cluster_id, state)
                return state
            
            if state in ["TERMINATED", "TERMINATED_WITH_ERRORS"]:
                logger.warning("Cluster %s was terminated early with state: %s", cluster_id, state)
                return state
                
            logger.info("Cluster is in state %s. Sleeping for %d seconds...", state, poll_interval)
            time.sleep(poll_interval)
            
        raise TimeoutError(f"EMR Cluster {cluster_id} did not reach target states {target_states} within {max_wait_seconds} seconds.")
