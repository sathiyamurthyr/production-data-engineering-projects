"""
Azure Databricks Cost Optimization & Cluster Resource Management
=================================================================
Production implementation of cost optimization patterns for Azure Databricks.

Business Use Case:
    Cloud compute & Databricks Unit (DBU) consumption can rapidly inflate cloud spending
    if clusters are over-provisioned, idle, or running expensive VM SKUs unnecessarily.
    This module enforces automated cost controls, cluster policies, Spot Instance usage,
    instance pool warm-up strategies, and idle auto-termination parameters.

Architecture & Cost Pillars:
    1. Cluster Policies: Governance limits restricting instance types, forcing auto-termination.
    2. Instance Pools: Reusable warm VM instances reducing cluster startup times (from 5m to 30s)
       without incurring full compute fees when idle.
    3. Azure Spot VMs: Leverage unused Azure compute at 60-80% discount for fault-tolerant worker nodes.
    4. Auto-scaling & Auto-termination: Dynamically scale workers (e.g., 2 to 10 nodes) and terminate
       clusters after 15-20 minutes of inactivity.
    5. Single Node Clusters: Use single-node driver-only clusters for non-distributed workload tasks.

Performance & Savings Matrix:
    - Driver Node: Always On-Demand (prevent driver loss due to spot eviction).
    - Worker Nodes: 100% Spot or Hybrid (e.g. 1 On-Demand base worker + rest Spot).
    - Cluster Auto-termination: 20 minutes (dev/test), 30 minutes (prod interactive).

Interview Questions:
    Q: What is a DBU in Azure Databricks and how is pricing calculated?
    A: A Databricks Unit (DBU) is a unit of processing capability per hour. Total cost = 
       (Azure VM infrastructure cost) + (Databricks DBU rate * DBUs consumed per hour).
       DBU rates vary by workload type (Jobs Compute is cheaper than Interactive SQL/All-Purpose Compute).

    Q: Why shouldn't driver nodes use Azure Spot instances?
    A: If Azure reclaims a Spot instance, the VM terminates immediately. If a worker node is evicted,
       Spark reassigns tasks to another worker. But if the driver node is evicted, the entire Spark Context
       and job state are lost.

    Q: How do Cluster Pools save costs and time?
    A: Pools maintain a warm supply of idle VMs with pre-installed OS images. This drops cluster start times
       from 5 minutes down to ~30 seconds. While idle in a pool, you pay only Azure VM hosting fees, not Databricks DBUs.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CostOptimizationManager")


@dataclass
class VMPriceModel:
    """Representation of Azure VM and Databricks DBU hourly cost rates."""
    vm_type: str
    vcpus: int
    ram_gb: float
    on_demand_vm_hourly: float
    spot_vm_hourly: float
    job_dbu_rate_hourly: float
    interactive_dbu_rate_hourly: float


class CostOptimizationManager:
    """
    Cost Optimization Manager providing estimation, policy enforcement,
    and recommended cluster configurations for Azure Databricks.
    """

    DEFAULT_VM_RATES = {
        "Standard_D4ds_v5": VMPriceModel(
            vm_type="Standard_D4ds_v5", vcpus=4, ram_gb=16.0,
            on_demand_vm_hourly=0.192, spot_vm_hourly=0.038,
            job_dbu_rate_hourly=0.15, interactive_dbu_rate_hourly=0.40
        ),
        "Standard_D8ds_v5": VMPriceModel(
            vm_type="Standard_D8ds_v5", vcpus=8, ram_gb=32.0,
            on_demand_vm_hourly=0.384, spot_vm_hourly=0.076,
            job_dbu_rate_hourly=0.30, interactive_dbu_rate_hourly=0.80
        ),
        "Standard_E16ds_v5": VMPriceModel(
            vm_type="Standard_E16ds_v5", vcpus=16, ram_gb=128.0,
            on_demand_vm_hourly=1.008, spot_vm_hourly=0.201,
            job_dbu_rate_hourly=0.60, interactive_dbu_rate_hourly=1.60
        )
    }

    def __init__(self, custom_rates: Optional[Dict[str, VMPriceModel]] = None):
        self.vm_rates = custom_rates or self.DEFAULT_VM_RATES

    def estimate_cluster_cost(
        self,
        vm_type: str,
        num_workers: int,
        duration_hours: float,
        is_job_cluster: bool = True,
        use_spot_workers: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate estimated cost for a given cluster run.
        Compares On-Demand vs Spot worker costs and Job vs Interactive DBU pricing.
        """
        if vm_type not in self.vm_rates:
            raise ValueError(f"Unknown VM type '{vm_type}'. Supported: {list(self.vm_rates.keys())}")

        rate = self.vm_rates[vm_type]
        num_nodes = num_workers + 1  # 1 Driver + N Workers

        # Driver is ALWAYS On-Demand
        driver_vm_cost = rate.on_demand_vm_hourly * duration_hours

        # Workers can be Spot or On-Demand
        worker_vm_hourly = rate.spot_vm_hourly if use_spot_workers else rate.on_demand_vm_hourly
        worker_vm_cost = (num_workers * worker_vm_hourly) * duration_hours

        total_vm_cost = driver_vm_cost + worker_vm_cost

        # DBU cost computation
        dbu_hourly_rate = rate.job_dbu_rate_hourly if is_job_cluster else rate.interactive_dbu_rate_hourly
        dbus_consumed = num_nodes * rate.vcpus * 0.75 * duration_hours  # Approx DBU multiplier
        total_dbu_cost = dbus_consumed * dbu_hourly_rate

        total_cost = total_vm_cost + total_dbu_cost

        # Compute savings vs non-optimized (100% On-Demand Interactive)
        baseline_vm = (num_nodes * rate.on_demand_vm_hourly) * duration_hours
        baseline_dbu = (num_nodes * rate.vcpus * 0.75 * duration_hours) * rate.interactive_dbu_rate_hourly
        baseline_total = baseline_vm + baseline_dbu

        savings_pct = max(0.0, ((baseline_total - total_cost) / baseline_total) * 100)

        return {
            "vm_type": vm_type,
            "num_workers": num_workers,
            "duration_hours": duration_hours,
            "use_spot_workers": use_spot_workers,
            "is_job_cluster": is_job_cluster,
            "driver_vm_cost_usd": round(driver_vm_cost, 2),
            "worker_vm_cost_usd": round(worker_vm_cost, 2),
            "total_vm_cost_usd": round(total_vm_cost, 2),
            "total_dbu_cost_usd": round(total_dbu_cost, 2),
            "total_estimated_cost_usd": round(total_cost, 2),
            "baseline_on_demand_interactive_cost_usd": round(baseline_total, 2),
            "estimated_savings_percent": round(savings_pct, 1)
        }

    def generate_cost_optimized_cluster_policy(self) -> Dict[str, Any]:
        """
        Generate enterprise cluster policy JSON that enforces auto-termination,
        approved VM family, Spot worker usage, and max worker caps.
        """
        policy = {
            "autotermination_minutes": {
                "type": "range",
                "minValue": 10,
                "maxValue": 30,
                "defaultValue": 20
            },
            "node_type_id": {
                "type": "allowlist",
                "values": ["Standard_D4ds_v5", "Standard_D8ds_v5", "Standard_E16ds_v5"],
                "defaultValue": "Standard_D4ds_v5"
            },
            "driver_node_type_id": {
                "type": "allowlist",
                "values": ["Standard_D4ds_v5", "Standard_D8ds_v5"],
                "defaultValue": "Standard_D4ds_v5"
            },
            "spark_conf.spark.databricks.cluster.profile": {
                "type": "fixed",
                "value": "singleNode",
                "hidden": True
            },
            "azure_attributes.availability": {
                "type": "allowlist",
                "values": ["SPOT_WITH_FALLBACK_AZURE", "SPOT_AZURE"],
                "defaultValue": "SPOT_WITH_FALLBACK_AZURE"
            },
            "autoscale.min_workers": {
                "type": "range",
                "minValue": 1,
                "maxValue": 2,
                "defaultValue": 1
            },
            "autoscale.max_workers": {
                "type": "range",
                "minValue": 2,
                "maxValue": 8,
                "defaultValue": 4
            }
        }
        logger.info("Generated cost-optimized Databricks Cluster Policy.")
        return policy


if __name__ == "__main__":
    cost_mgr = CostOptimizationManager()
    estimate = cost_mgr.estimate_cluster_cost(
        vm_type="Standard_D4ds_v5",
        num_workers=4,
        duration_hours=10.0,
        is_job_cluster=True,
        use_spot_workers=True
    )
    print("Cost Estimate Summary:")
    print(json.dumps(estimate, indent=2))
