"""
EMR Cluster Configuration builder module.
Provides programmatic creation of Instance Groups, Instance Fleets,
Bootstrap Actions, Security Groups, and Spark/Hive settings classification.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

from typing import Dict, Any, List, Optional


class EMRClusterConfigBuilder:
    """
    Builder utility for Amazon EMR cluster execution configurations.
    """

    def __init__(self, cluster_name: str, release_label: str = "emr-6.13.0"):
        self.config: Dict[str, Any] = {
            "Name": cluster_name,
            "ReleaseLabel": release_label,
            "VisibleToAllUsers": True,
            "Applications": [
                {"Name": "Hadoop"},
                {"Name": "Spark"},
                {"Name": "Hive"}
            ],
            "Instances": {
                "KeepJobFlowAliveWhenNoSteps": False,
                "TerminationProtected": False
            },
            "Configurations": [],
            "BootstrapActions": [],
            "ScaleDownBehavior": "TERMINATE_AT_TASK_COMPLETION"
        }

    def with_applications(self, apps: List[str]) -> "EMRClusterConfigBuilder":
        """
        Sets EMR applications to be installed (e.g. ['Spark', 'Hive', 'Hadoop', 'Presto']).
        """
        self.config["Applications"] = [{"Name": app} for app in apps]
        return self

    def with_logging(self, s3_log_uri: str) -> "EMRClusterConfigBuilder":
        """
        Sets the S3 bucket destination for EMR logs.
        """
        if not s3_log_uri.startswith("s3://"):
            raise ValueError("Log URI must start with s3://")
        self.config["LogUri"] = s3_log_uri
        return self

    def with_roles(self, service_role: str = "EMR_DefaultRole", job_flow_role: str = "EMR_EC2_DefaultRole") -> "EMRClusterConfigBuilder":
        """
        Configures the IAM Roles for EMR Service and EC2 Instance Profile.
        """
        self.config["ServiceRole"] = service_role
        self.config["JobFlowRole"] = job_flow_role
        return self

    def with_network(self, subnet_id: str, master_sg_id: Optional[str] = None, slave_sg_id: Optional[str] = None, service_access_sg_id: Optional[str] = None) -> "EMRClusterConfigBuilder":
        """
        Configures network and security group configurations.
        """
        self.config["Instances"]["Ec2SubnetId"] = subnet_id
        if master_sg_id:
            self.config["Instances"]["EmrManagedMasterSecurityGroup"] = master_sg_id
        if slave_sg_id:
            self.config["Instances"]["EmrManagedSlaveSecurityGroup"] = slave_sg_id
        if service_access_sg_id:
            self.config["Instances"]["ServiceAccessSecurityGroup"] = service_access_sg_id
        return self

    def with_instance_groups(
        self,
        master_type: str = "m5.xlarge",
        core_type: str = "r5.xlarge",
        core_count: int = 2,
        task_type: Optional[str] = None,
        task_count: int = 0,
        ebs_size_gb: int = 64
    ) -> "EMRClusterConfigBuilder":
        """
        Configures the cluster using the Instance Groups model (fixed counts).
        """
        # Reset fleets if set previously
        if "InstanceFleets" in self.config["Instances"]:
            del self.config["Instances"]["InstanceFleets"]

        ebs_config = {
            "EbsBlockDeviceConfigs": [
                {
                    "VolumeSpecification": {
                        "VolumeType": "gp3",
                        "SizeInGB": ebs_size_gb
                    },
                    "VolumesPerInstance": 1
                }
              ]
        }

        instance_groups = [
            {
                "Name": "PrimaryNode",
                "Market": "ON_DEMAND",
                "InstanceRole": "MASTER",
                "InstanceType": master_type,
                "InstanceCount": 1,
                "EbsConfiguration": ebs_config
            },
            {
                "Name": "CoreNodes",
                "Market": "ON_DEMAND",
                "InstanceRole": "CORE",
                "InstanceType": core_type,
                "InstanceCount": core_count,
                "EbsConfiguration": ebs_config
            }
        ]

        if task_type and task_count > 0:
            instance_groups.append({
                "Name": "TaskNodes",
                "Market": "SPOT",  # Task nodes are default Spot for cost optimization
                "InstanceRole": "TASK",
                "InstanceType": task_type,
                "InstanceCount": task_count,
                "EbsConfiguration": ebs_config
            })

        self.config["Instances"]["InstanceGroups"] = instance_groups
        return self

    def with_instance_fleets(
        self,
        master_types: List[str],
        core_types: List[str],
        task_types: List[str],
        target_core_ondemand: int = 2,
        target_task_spot: int = 4
    ) -> "EMRClusterConfigBuilder":
        """
        Configures the cluster using the Instance Fleets model (resilient, multi-instance types).
        """
        # Reset groups if set previously
        if "InstanceGroups" in self.config["Instances"]:
            del self.config["Instances"]["InstanceGroups"]

        fleets = [
            {
                "Name": "MasterFleet",
                "InstanceFleetType": "MASTER",
                "TargetOnDemandCapacity": 1,
                "TargetSpotCapacity": 0,
                "InstanceTypeConfigs": [
                    {
                        "InstanceType": itype,
                        "WeightedCapacity": 1,
                        "EbsConfiguration": {
                            "EbsBlockDeviceConfigs": [{
                                "VolumeSpecification": {"VolumeType": "gp3", "SizeInGB": 64},
                                "VolumesPerInstance": 1
                            }]
                        }
                    } for itype in master_types
                ]
            },
            {
                "Name": "CoreFleet",
                "InstanceFleetType": "CORE",
                "TargetOnDemandCapacity": target_core_ondemand,
                "TargetSpotCapacity": 0,
                "InstanceTypeConfigs": [
                    {
                        "InstanceType": itype,
                        "WeightedCapacity": 1,
                        "EbsConfiguration": {
                            "EbsBlockDeviceConfigs": [{
                                "VolumeSpecification": {"VolumeType": "gp3", "SizeInGB": 128},
                                "VolumesPerInstance": 1
                            }]
                        }
                    } for itype in core_types
                ]
            },
            {
                "Name": "TaskFleet",
                "InstanceFleetType": "TASK",
                "TargetOnDemandCapacity": 0,
                "TargetSpotCapacity": target_task_spot,
                "InstanceTypeConfigs": [
                    {
                        "InstanceType": itype,
                        "WeightedCapacity": 1,
                        "BidPriceAsPercentageOfOnDemandPrice": 100.0,
                        "EbsConfiguration": {
                            "EbsBlockDeviceConfigs": [{
                                "VolumeSpecification": {"VolumeType": "gp3", "SizeInGB": 64},
                                "VolumesPerInstance": 1
                            }]
                        }
                    } for itype in task_types
                ]
            }
        ]

        self.config["Instances"]["InstanceFleets"] = fleets
        return self

    def add_bootstrap_action(self, name: str, s3_script_path: str, args: Optional[List[str]] = None) -> "EMRClusterConfigBuilder":
        """
        Adds a bootstrap action to run before Hadoop/Spark packages start on each instance.
        """
        if not s3_script_path.startswith("s3://"):
            raise ValueError("Bootstrap script path must be an S3 URI (s3://...)")
            
        self.config["BootstrapActions"].append({
            "Name": name,
            "ScriptBootstrapAction": {
                "Path": s3_script_path,
                "Args": args or []
            }
        })
        return self

    def add_configuration(self, classification: str, properties: Dict[str, str], nested_configurations: Optional[List[Dict[str, Any]]] = None) -> "EMRClusterConfigBuilder":
        """
        Adds configuration classifications (e.g. spark-defaults, yarn-site, hive-site) to customize settings.
        """
        config_item: Dict[str, Any] = {
            "Classification": classification,
            "Properties": properties
        }
        if nested_configurations:
            config_item["Configurations"] = nested_configurations

        # Ensure we don't duplicate classification; update if exists
        for idx, item in enumerate(self.config["Configurations"]):
            if item["Classification"] == classification:
                self.config["Configurations"][idx]["Properties"].update(properties)
                if nested_configurations:
                    self.config["Configurations"][idx]["Configurations"] = nested_configurations
                return self

        self.config["Configurations"].append(config_item)
        return self

    def build(self) -> Dict[str, Any]:
        """
        Validates and returns the final EMR configuration dictionary.
        """
        # Ensure we have instance configuration
        if "InstanceGroups" not in self.config["Instances"] and "InstanceFleets" not in self.config["Instances"]:
            # Setup standard instance groups if nothing was specified
            self.with_instance_groups()

        # Validate mandatory parts
        if "ServiceRole" not in self.config or "JobFlowRole" not in self.config:
            self.with_roles()

        return self.config
