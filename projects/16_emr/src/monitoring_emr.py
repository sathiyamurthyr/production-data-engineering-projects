"""
Monitoring and metrics collection for Amazon EMR.
Provides CloudWatch API queries for cluster health metrics (Memory, Nodes, Idle Status)
and queries the YARN Resource Manager HTTP REST API.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
import requests
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EMRMonitoring")


class EMRMonitor:
    """
    Retrieves and evaluates operational metrics for EMR Clusters from CloudWatch and YARN Resource Manager.
    """

    def __init__(self, region_name: str = "us-east-1"):
        self.cloudwatch = boto3.client("cloudwatch", region_name=region_name)

    def get_cluster_cloudwatch_metrics(
        self,
        cluster_id: str,
        metric_name: str,
        minutes_back: int = 60,
        period_seconds: int = 300,
        statistics: List[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves metric data for a specific EMR cluster from Amazon CloudWatch.
        Common EMR MetricNames:
          - YARNMemoryAvailablePercentage
          - ContainerPendingRatio
          - IsIdle
          - LiveNodes
          - RemainingMapTasksPerSlot
        """
        statistics = statistics or ["Average"]
        start_time = datetime.utcnow() - timedelta(minutes=minutes_back)
        end_time = datetime.utcnow()
        
        logger.info("Querying CloudWatch metric '%s' for EMR Cluster %s...", metric_name, cluster_id)
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/ElasticMapReduce",
                MetricName=metric_name,
                Dimensions=[
                    {
                        "Name": "JobFlowId",
                        "Value": cluster_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period_seconds,
                Statistics=statistics,
                Unit="Percent" if "Percent" in metric_name else "Count"
            )
            return response
        except ClientError as ce:
            logger.error("Failed to query CloudWatch metrics: %s", ce.response["Error"]["Message"])
            raise

    def check_cluster_resource_health(self, cluster_id: str) -> Dict[str, Any]:
        """
        Gathers a high-level health report of key metrics from CloudWatch.
        """
        metrics = ["YARNMemoryAvailablePercentage", "ContainerPendingRatio", "IsIdle", "LiveNodes"]
        report = {}
        for m in metrics:
            try:
                res = self.get_cluster_cloudwatch_metrics(cluster_id, m, minutes_back=15, period_seconds=300)
                datapoints = res.get("Datapoints", [])
                if datapoints:
                    # Sort by time to get the latest reading
                    datapoints.sort(key=lambda x: x["Timestamp"])
                    latest_val = datapoints[-1].get("Average", datapoints[-1].get("Sum", 0.0))
                    report[m] = latest_val
                else:
                    report[m] = None
            except Exception as e:
                logger.warning("Failed to collect health metric %s: %s", m, str(e))
                report[m] = "ERROR"
        return report


class YarnResourceManagerClient:
    """
    Communicates with the Apache Hadoop YARN Resource Manager API on the Primary Node.
    """

    def __init__(self, master_public_dns: str, port: int = 8088):
        """
        :param master_public_dns: The public DNS/IP address of the EMR Master Node.
        :param port: The YARN Resource Manager REST Web service port (default is 8088).
        """
        self.base_url = f"http://{master_public_dns}:{port}/ws/v1/cluster"

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """
        Retrieves live cluster metrics from YARN Resource Manager.
        Exposes allocated/available vCores, memory, active/lost nodes, and application queue sizes.
        """
        url = f"{self.base_url}/metrics"
        logger.info("Querying YARN metrics: %s", url)
        try:
            # Set a low timeout so we don't block pipeline operations if cluster is unreachable
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json().get("clusterMetrics", {})
        except requests.exceptions.RequestException as re:
            logger.error("YARN ResourceManager is unreachable at %s. Error: %s", url, str(re))
            # Return dummy state for fallback/testing
            return {
                "yarnConnectionStatus": "UNREACHABLE",
                "appsSubmitted": 0,
                "appsCompleted": 0,
                "allocatedMB": 0,
                "availableMB": 0,
                "allocatedVCores": 0,
                "availableVCores": 0,
                "activeNodes": 0
            }

    def list_yarn_applications(self, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists details of applications executing in the YARN cluster.
        :param state_filter: Optional filter (e.g., 'RUNNING', 'ACCEPTED', 'FINISHED').
        """
        url = f"{self.base_url}/apps"
        params = {}
        if state_filter:
            params["state"] = state_filter

        logger.info("Querying YARN Applications: %s with filter %s", url, state_filter)
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json().get("apps", {}).get("app", [])
        except requests.exceptions.RequestException as re:
            logger.error("Failed to query YARN applications: %s", str(re))
            return []
