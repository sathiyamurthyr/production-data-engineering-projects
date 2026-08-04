"""AWS Glue Connector - AWS Glue metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class AWSGlueConnector(BaseConnector):
    """Harvest metadata from AWS Glue."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize AWS Glue connector."""
        super().__init__(config)
        self.platform_name = "aws_glue"
        self.region = config.get("region", "us-east-1")
        self.database = config.get("database", "default")
        self.aws_access_key_id = config.get("aws_access_key_id", "")
        self.aws_secret_access_key = config.get("aws_secret_access_key", "")

    def test_connection(self) -> bool:
        """Test connection to AWS Glue."""
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            client.get_databases()
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all tables from AWS Glue."""
        assets = []
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            paginator = client.get_paginator("get_tables")
            for page in paginator.paginate(DatabaseName=self.database):
                for table in page["TableList"]:
                    asset = self._table_to_asset(table)
                    assets.append(asset)
        except Exception as e:
            print(f"Error fetching Glue assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific table by name."""
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            response = client.get_table(DatabaseName=self.database, Name=asset_id)
            return self._table_to_asset(response["Table"])
        except Exception as e:
            print(f"Error fetching table {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from AWS Glue DataBrew or Lake Formation."""
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get table schema from AWS Glue."""
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            response = client.get_table(DatabaseName=self.database, Name=asset_id)
            columns = []
            for col in response["Table"]["StorageDescriptor"]["Columns"]:
                columns.append({
                    "name": col["Name"],
                    "type": col["Type"],
                    "nullable": True,
                    "primary_key": False,
                })
            return {"columns": columns}
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {"columns": []}

    def _table_to_asset(self, table: dict[str, Any]) -> Asset:
        """Convert Glue table to Asset."""
        storage_descriptor = table.get("StorageDescriptor", {})
        return Asset(
            name=table["Name"],
            description=table.get("Description", f"AWS Glue table in {self.database}"),
            asset_type=AssetType.TABLE,
            platform="aws_glue",
            platform_id=f"{self.database}.{table['Name']}",
            domain=self.database,
            owner=table.get("Owner"),
            tags=["aws", "glue", self.database],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "database": self.database,
                "table_type": table.get("TableType", "EXTERNAL_TABLE"),
                "location": storage_descriptor.get("Location", ""),
                "input_format": storage_descriptor.get("InputFormat", ""),
                "output_format": storage_descriptor.get("OutputFormat", ""),
                "serde_info": storage_descriptor.get("SerdeInfo", {}),
            },
        )

    def get_crawlers(self) -> list[dict[str, Any]]:
        """Get all Glue crawlers."""
        crawlers = []
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            paginator = client.get_paginator("get_crawlers")
            for page in paginator.paginate():
                for crawler in page["Crawlers"]:
                    crawlers.append({
                        "name": crawler["Name"],
                        "database_name": crawler.get("DatabaseName", ""),
                        "targets": crawler.get("Targets", {}),
                        "schedule": crawler.get("Schedule", {}),
                        "state": crawler.get("State", "READY"),
                    })
        except Exception as e:
            print(f"Error fetching crawlers: {e}")
        return crawlers

    def get_jobs(self) -> list[dict[str, Any]]:
        """Get all Glue jobs."""
        jobs = []
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            paginator = client.get_paginator("get_jobs")
            for page in paginator.paginate():
                for job in page["Jobs"]:
                    jobs.append({
                        "name": job["Name"],
                        "description": job.get("Description", ""),
                        "role": job.get("Role", ""),
                        "command": job.get("Command", {}),
                        "created_on": job.get("CreatedOn", ""),
                        "last_modified_on": job.get("LastModifiedOn", ""),
                    })
        except Exception as e:
            print(f"Error fetching jobs: {e}")
        return jobs

    def get_triggers(self) -> list[dict[str, Any]]:
        """Get all Glue triggers."""
        triggers = []
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            paginator = client.get_paginator("get_triggers")
            for page in paginator.paginate():
                for trigger in page["Triggers"]:
                    triggers.append({
                        "name": trigger["Name"],
                        "type": trigger.get("Type", "SCHEDULED"),
                        "state": trigger.get("State", "CREATED"),
                        "actions": trigger.get("Actions", []),
                    })
        except Exception as e:
            print(f"Error fetching triggers: {e}")
        return triggers

    def get_workflows(self) -> list[dict[str, Any]]:
        """Get all Glue workflows."""
        workflows = []
        try:
            import boto3
            client = boto3.client(
                "glue",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            paginator = client.get_paginator("list_workflows")
            for page in paginator.paginate():
                for workflow_name in page.get("Workflows", []):
                    workflow = client.get_workflow(Name=workflow_name)
                    workflows.append({
                        "name": workflow_name,
                        "description": workflow.get("Workflow", {}).get("Description", ""),
                        "state": workflow.get("Workflow", {}).get("State", ""),
                    })
        except Exception as e:
            print(f"Error fetching workflows: {e}")
        return workflows