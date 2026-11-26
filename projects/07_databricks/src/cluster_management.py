"""
Module 11: Cluster Management — Policies, Instance Pools, and Autoscaling Governance
======================================================================================

Explanation:
    Databricks compute resources can be dynamically provisioned, scaled, and policy-governed.
    Cluster policies allow admins to enforce resource limits (instance types, max workers, DBR version),
    tagging rules (cost center allocation), and autoscaling parameters to prevent unexpected spending.

Business Use Case:
    - Enforcing mandatory cost-center tags (`environment`, `owner`, `cost_center`) on all compute nodes.
    - Provisioning Instance Pools to keep pre-attached warm EC2/VM instances for instant job startup (<30s).
    - Preventing users from launching excessively large or expensive instance types (e.g. i3.16xlarge) for small tasks.
    - Managing Single-Node clusters for small developer workloads vs Multi-Node autoscaling clusters for production.

Architecture:
    Cluster Policy Definition (JSON Spec)
                  |
    Databricks Clusters API / Terraform
                  |
    +-------------------------------------------------------------+
    |                     Cluster Provisioning                    |
    |  +---------------------+        +------------------------+  |
    |  | Instance Pool       | ---->  | Autoscaling Workers    |  |
    |  | (Pre-warmed Nodes)  |        | (Min: 2, Max: 32)      |  |
    |  +---------------------+        +------------------------+  |
    +-------------------------------------------------------------+

Performance Notes:
    - Instance pools reduce cluster spin-up time from ~5 minutes down to ~30 seconds by keeping VM disk images pre-loaded.
    - Autoscaling scales down idle workers based on Spark metrics after 10 minutes of inactivity.

Common Mistakes:
    - Disabling auto-termination on interactive development clusters, leading to runaway costs over weekends.
    - Using single-node compute for heavy parallel PySpark jobs (causes OutOfMemory errors).
    - Hardcoding AWS/Azure VM SKU types across environments where specific SKUs may not be available.

Interview Questions:
    Q: What is a Databricks Cluster Policy and why is it essential for enterprise governance?
    A: A Cluster Policy is a JSON document restricting the set of configurable options when creating a cluster.
       It enforces constraints like max worker counts, allowed VM instance types, required tags, and mandatory auto-termination.

    Q: How do Instance Pools improve job execution efficiency?
    A: Instance Pools maintain a set of idle, pre-acquired VM instances. When a job runs, it acquires VMs from the pool
       instantly without waiting for the cloud provider to allocate, boot, and initialize new virtual machines.
"""

import logging
import json
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabricksClusterManager:
    """
    Production-grade helper for configuring Databricks cluster specs,
    autoscaling bounds, cluster policies, and instance pool definitions.
    """

    def __init__(self, dbr_version: str = "14.3.x-scala2.12"):
        self.dbr_version = dbr_version

    def build_cluster_spec(
        self,
        cluster_name: str,
        node_type: str = "i3.xlarge",
        min_workers: int = 2,
        max_workers: int = 10,
        autotermination_minutes: int = 60,
        custom_tags: Optional[Dict[str, str]] = None,
        spark_conf: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Builds a standard Databricks Clusters API v2.0 creation payload.
        """
        tags = {
            "Environment": "Production",
            "ManagedBy": "DataEngineeringDiaries",
            "Project": "DatabricksPlatform",
        }
        if custom_tags:
            tags.update(custom_tags)

        s_conf = {
            "spark.sql.adaptive.enabled": "true",
            "spark.databricks.delta.preview.enabled": "true",
        }
        if spark_conf:
            s_conf.update(spark_conf)

        cluster_spec = {
            "cluster_name": cluster_name,
            "spark_version": self.dbr_version,
            "node_type_id": node_type,
            "driver_node_type_id": node_type,
            "autoscale": {
                "min_workers": min_workers,
                "max_workers": max_workers,
            },
            "autotermination_minutes": autotermination_minutes,
            "custom_tags": tags,
            "spark_conf": s_conf,
        }
        logger.info(f"Built Cluster Spec for '{cluster_name}' ({min_workers}-{max_workers} workers)")
        return cluster_spec

    def build_single_node_cluster_spec(
        self,
        cluster_name: str,
        node_type: str = "i3.xlarge",
        autotermination_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        Builds a lightweight Single-Node cluster spec for developer testing or lightweight jobs.
        """
        spec = self.build_cluster_spec(
            cluster_name=cluster_name,
            node_type=node_type,
            min_workers=0,
            max_workers=0,
            autotermination_minutes=autotermination_minutes,
            spark_conf={
                "spark.master": "local[*]",
                "spark.databricks.cluster.profile": "singleNode",
            },
            custom_tags={"NodeType": "SingleNodeDev"},
        )
        # Remove autoscale for single-node
        spec.pop("autoscale", None)
        spec["num_workers"] = 0
        return spec

    def build_cluster_policy_json(self, max_workers_limit: int = 16) -> str:
        """
        Generates standard Databricks Cluster Policy JSON enforcing auto-termination,
        tagging rules, and instance limits.
        """
        policy = {
            "autotermination_minutes": {
                "type": "range",
                "maxValue": 120,
                "defaultValue": 30,
            },
            "autoscale.max_workers": {
                "type": "range",
                "maxValue": max_workers_limit,
                "defaultValue": 8,
            },
            "custom_tags.CostCenter": {
                "type": "pattern",
                "pattern": "CC-[0-9]{4}",
                "defaultValue": "CC-1001",
            },
            "spark_conf.spark.sql.adaptive.enabled": {
                "type": "fixed",
                "value": "true",
            },
        }
        return json.dumps(policy, indent=2)

    def build_instance_pool_spec(
        self,
        pool_name: str,
        node_type: str = "i3.xlarge",
        min_idle_instances: int = 1,
        max_capacity: int = 20,
        idle_instance_autotermination_minutes: int = 15,
    ) -> Dict[str, Any]:
        """
        Builds payload for creating a Databricks Instance Pool.
        """
        pool_spec = {
            "instance_pool_name": pool_name,
            "node_type_id": node_type,
            "min_idle_instances": min_idle_instances,
            "max_capacity": max_capacity,
            "idle_instance_autotermination_minutes": idle_instance_autotermination_minutes,
        }
        logger.info(f"Built Instance Pool Spec for '{pool_name}' (Min Idle: {min_idle_instances})")
        return pool_spec


if __name__ == "__main__":
    cm = DatabricksClusterManager()

    print("=== Multi-Node Production Cluster Spec ===")
    prod_spec = cm.build_cluster_spec("prod_etl_cluster", min_workers=4, max_workers=20)
    print(json.dumps(prod_spec, indent=2))

    print("\n=== Single Node Dev Cluster Spec ===")
    dev_spec = cm.build_single_node_cluster_spec("dev_sandbox")
    print(json.dumps(dev_spec, indent=2))

    print("\n=== Cluster Governance Policy JSON ===")
    print(cm.build_cluster_policy_json(max_workers_limit=32))
