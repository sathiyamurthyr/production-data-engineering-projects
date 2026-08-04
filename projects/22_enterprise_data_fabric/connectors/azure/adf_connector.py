"""Azure Data Factory Connector - ADF metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class ADFConnector(BaseConnector):
    """Harvest metadata from Azure Data Factory."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize ADF connector."""
        super().__init__(config)
        self.platform_name = "azure_data_factory"
        self.subscription_id = config.get("subscription_id", "")
        self.resource_group_name = config.get("resource_group_name", "")
        self.factory_name = config.get("factory_name", "")
        self.credential = config.get("credential", None)

    def test_connection(self) -> bool:
        """Test connection to Azure Data Factory."""
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            client.factories.get(self.resource_group_name, self.factory_name)
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all pipelines from ADF."""
        assets = []
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            pipelines = client.pipelines.list_by_factory(
                self.resource_group_name, self.factory_name
            )
            for pipeline in pipelines:
                asset = self._pipeline_to_asset(pipeline)
                assets.append(asset)
        except Exception as e:
            print(f"Error fetching ADF assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific pipeline by name."""
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            pipeline = client.pipelines.get(
                self.resource_group_name, self.factory_name, asset_id
            )
            return self._pipeline_to_asset(pipeline)
        except Exception as e:
            print(f"Error fetching pipeline {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from ADF pipeline activities."""
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get pipeline schema (activities, parameters)."""
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            pipeline = client.pipelines.get(
                self.resource_group_name, self.factory_name, asset_id
            )
            return {
                "activities": [act.name for act in pipeline.activities] if pipeline.activities else [],
                "parameters": list(pipeline.parameters.keys()) if pipeline.parameters else [],
            }
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {"activities": [], "parameters": []}

    def _pipeline_to_asset(self, pipeline: Any) -> Asset:
        """Convert ADF pipeline to Asset."""
        return Asset(
            name=pipeline.name,
            description=pipeline.description or f"ADF pipeline in {self.factory_name}",
            asset_type=AssetType.PIPELINE,
            platform="azure_data_factory",
            platform_id=f"{self.factory_name}/{pipeline.name}",
            domain=self.resource_group_name,
            tags=["azure", "adf", "pipeline"],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "factory_name": self.factory_name,
                "resource_group": self.resource_group_name,
                "subscription_id": self.subscription_id,
            },
        )

    def get_data_sources(self) -> list[dict[str, Any]]:
        """Get all linked services (data sources)."""
        data_sources = []
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            linked_services = client.linked_services.list_by_factory(
                self.resource_group_name, self.factory_name
            )
            for ls in linked_services:
                data_sources.append({
                    "name": ls.name,
                    "type": ls.type,
                    "description": ls.description,
                })
        except Exception as e:
            print(f"Error fetching data sources: {e}")
        return data_sources

    def get_datasets(self) -> list[Asset]:
        """Get all datasets."""
        assets = []
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            datasets = client.datasets.list_by_factory(
                self.resource_group_name, self.factory_name
            )
            for ds in datasets:
                asset = Asset(
                    name=ds.name,
                    description=ds.description or f"ADF dataset in {self.factory_name}",
                    asset_type=AssetType.TABLE,
                    platform="azure_data_factory",
                    platform_id=f"{self.factory_name}/{ds.name}",
                    domain=self.resource_group_name,
                    tags=["azure", "adf", "dataset"],
                    sensitivity=SensitivityLevel.INTERNAL,
                    metadata={
                        "factory_name": self.factory_name,
                        "linked_service_name": ds.properties.linked_service_name.reference_name if ds.properties and ds.properties.linked_service_name else "",
                    },
                )
                assets.append(asset)
        except Exception as e:
            print(f"Error fetching datasets: {e}")
        return assets

    def get_triggers(self) -> list[dict[str, Any]]:
        """Get all triggers."""
        triggers = []
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            adf_triggers = client.triggers.list_by_factory(
                self.resource_group_name, self.factory_name
            )
            for trigger in adf_triggers:
                triggers.append({
                    "name": trigger.name,
                    "type": trigger.properties.type if trigger.properties else None,
                    "state": trigger.properties.state if trigger.properties else None,
                })
        except Exception as e:
            print(f"Error fetching triggers: {e}")
        return triggers

    def get_integration_runtimes(self) -> list[dict[str, Any]]:
        """Get all integration runtimes."""
        runtimes = []
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.identity import DefaultAzureCredential
            
            credential = self.credential or DefaultAzureCredential()
            client = DataFactoryManagementClient(credential, self.subscription_id)
            
            irs = client.integration_runtimes.list_by_factory(
                self.resource_group_name, self.factory_name
            )
            for ir in irs:
                runtimes.append({
                    "name": ir.name,
                    "type": ir.type,
                    "state": ir.properties.state if ir.properties else None,
                })
        except Exception as e:
            print(f"Error fetching integration runtimes: {e}")
        return runtimes