"""
Cost optimization strategies for AWS EMR.
Provides programmatic setups for Spot Instance Fleets, EMR Managed Scaling Policies,
and dynamic Task Node scaling based on resource needs.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import logging
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EMRCostOptimization")


class EMRCostOptimizer:
    """
    Orchestrates cost savings on AWS EMR via Spot instance fleets, auto-scaling policy mappings, and fleet resizing.
    """

    def __init__(self, emr_client: Optional[Any] = None, region_name: str = "us-east-1"):
        self.emr_client = emr_client or boto3.client("elasticmapreduce", region_name=region_name)

    @staticmethod
    def get_spot_optimized_fleet_config(
        subnet_id: str,
        on_demand_core_capacity: int = 2,
        spot_task_capacity: int = 8,
        spot_bid_percentage: float = 100.0
    ) -> Dict[str, Any]:
        """
        Generates an Instance Fleet configuration optimized for Spot instance task nodes.
        By placing master/core on On-Demand and tasks on Spot, we guarantee HDFS stability
        while scaling compute capacity with up to 90% cost savings.
        """
        logger.info("Generating spot-optimized EMR Instance Fleet configuration...")
        
        return {
            "Ec2SubnetIds": [subnet_id],
            "KeepJobFlowAliveWhenNoSteps": False,
            "TerminationProtected": False,
            "InstanceFleets": [
                {
                    "Name": "MasterFleet",
                    "InstanceFleetType": "MASTER",
                    "TargetOnDemandCapacity": 1,
                    "TargetSpotCapacity": 0,
                    "InstanceTypeConfigs": [
                        {"InstanceType": "m5.xlarge", "WeightedCapacity": 1}
                    ]
                },
                {
                    "Name": "CoreFleet",
                    "InstanceFleetType": "CORE",
                    "TargetOnDemandCapacity": on_demand_core_capacity,
                    "TargetSpotCapacity": 0,
                    "InstanceTypeConfigs": [
                        {"InstanceType": "r5.xlarge", "WeightedCapacity": 1},
                        {"InstanceType": "m5.2xlarge", "WeightedCapacity": 2}
                    ]
                },
                {
                    "Name": "TaskFleet",
                    "InstanceFleetType": "TASK",
                    "TargetOnDemandCapacity": 0,
                    "TargetSpotCapacity": spot_task_capacity,
                    "InstanceTypeConfigs": [
                        {
                            "InstanceType": "r5.xlarge", 
                            "WeightedCapacity": 1,
                            "BidPriceAsPercentageOfOnDemandPrice": spot_bid_percentage
                        },
                        {
                            "InstanceType": "m5.xlarge", 
                            "WeightedCapacity": 1,
                            "BidPriceAsPercentageOfOnDemandPrice": spot_bid_percentage
                        },
                        {
                            "InstanceType": "c5.2xlarge",
                            "WeightedCapacity": 2,
                            "BidPriceAsPercentageOfOnDemandPrice": spot_bid_percentage
                        }
                    ]
                }
            ]
        }

    def attach_managed_scaling_policy(
        self,
        cluster_id: str,
        min_capacity: int = 2,
        max_capacity: int = 30,
        on_demand_limit: Optional[int] = None
    ) -> None:
        """
        Attaches a Managed Scaling Policy to an EMR Cluster.
        EMR Managed Scaling automatically resizes clusters based on YARN workloads.
        """
        logger.info("Attaching Managed Scaling Policy to cluster %s...", cluster_id)
        try:
            # Define limits for On-Demand and Spot instances (measured in EMR units / instances)
            compute_limits = {
                "MinimumCapacityUnits": min_capacity,
                "MaximumCapacityUnits": max_capacity,
                "UnitType": "InstanceFleetUnits"  # Can also be 'Instances' or 'VCPU'
            }
            if on_demand_limit:
                compute_limits["MaximumOnDemandCapacityUnits"] = on_demand_limit
                
            response = self.emr_client.put_managed_scaling_policy(
                ClusterId=cluster_id,
                ManagedScalingPolicy={
                    "ComputeLimits": compute_limits
                }
            )
            logger.info("Successfully configured Managed Scaling for cluster %s. Response: %s", cluster_id, response)
        except ClientError as ce:
            logger.error("Failed to attach scaling policy to %s: %s", cluster_id, ce.response["Error"]["Message"])
            raise

    def resize_task_fleet(
        self,
        cluster_id: str,
        task_fleet_id: str,
        target_spot_capacity: int,
        target_on_demand_capacity: int = 0
    ) -> None:
        """
        Manually scales the Instance Fleet capacity for tasks.
        Use this when running large scheduled Spark runs where you want to warm up/scale down resources.
        """
        logger.info("Resizing Task Fleet %s on EMR Cluster %s. Spot capacity target: %d, On-Demand: %d", 
                    task_fleet_id, cluster_id, target_spot_capacity, target_on_demand_capacity)
        try:
            self.emr_client.modify_instance_fleet(
                ClusterId=cluster_id,
                InstanceFleet={
                    "InstanceFleetId": task_fleet_id,
                    "TargetOnDemandCapacity": target_on_demand_capacity,
                    "TargetSpotCapacity": target_spot_capacity
                }
            )
            logger.info("Successfully updated task fleet capacity.")
        except ClientError as ce:
            logger.error("Failed to modify instance fleet %s: %s", task_fleet_id, ce.response["Error"]["Message"])
            raise

    def get_cluster_fleet_ids(self, cluster_id: str) -> Dict[str, str]:
        """
        Helper method to retrieve fleet IDs (MASTER, CORE, TASK) for a given EMR cluster.
        """
        try:
            response = self.emr_client.list_instance_fleets(ClusterId=cluster_id)
            fleets = response.get("InstanceFleets", [])
            fleet_map = {}
            for fleet in fleets:
                fleet_type = fleet["InstanceFleetType"]
                fleet_id = fleet["Id"]
                fleet_map[fleet_type] = fleet_id
            return fleet_map
        except ClientError as ce:
            logger.error("Failed to list fleets for %s: %s", cluster_id, ce.response["Error"]["Message"])
            raise
