"""
adf_client.py - Azure Data Factory Management Client
=====================================================
Production ADF management client with Azure service principal authentication & fallback mocking.

Explanation:
    This module wraps the azure-mgmt-datafactory DataFactoryManagementClient
    with proper authentication, retry logic, configuration management, and fallback mocking
    for local offline development and testing.

Business Use Case:
    Every ADF automation script needs a properly configured management client.
    This module centralizes auth, config, client lifecycle management, and mock capabilities
    so all other modules can share a single authenticated or simulated client instance.

Authentication Flow:
    1. Service Principal (prod): AZURE_CLIENT_ID + AZURE_CLIENT_SECRET + AZURE_TENANT_ID
    2. DefaultAzureCredential (dev): Falls back through environment vars, managed identity, CLI
    3. Mock Client (testing/offline): Fallback when credentials are dummy or MOCK_ADF=true

Production Example:
    client = ADFClient.from_environment()
    adf = client.get_management_client()
    factories = list(adf.factories.list())

Interview Questions:
    Q: What is the difference between DefaultAzureCredential and ClientSecretCredential?
    A: DefaultAzureCredential tries multiple auth methods in order (env vars, managed identity,
       VS Code, CLI). ClientSecretCredential uses explicit service principal credentials.
       Use DefaultAzureCredential for flexibility; ClientSecretCredential for explicit control.

    Q: How do you secure ADF credentials in production?
    A: Use Azure Key Vault to store connection strings and secrets. ADF has native Key Vault
       integration - linked services can reference Key Vault secrets directly instead of
       storing plaintext credentials in ADF.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.resource import ResourceManagementClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ADFConfig:
    """
    Configuration dataclass for Azure Data Factory management.

    Attributes:
        tenant_id:         Azure Active Directory tenant ID
        client_id:         Service principal application (client) ID
        client_secret:     Service principal client secret
        subscription_id:   Azure subscription ID
        resource_group:    Default resource group for ADF resources
        factory_name:      Default ADF factory name
        use_default_cred:  Use DefaultAzureCredential instead of service principal
        mock_mode:         Enable fallback mock client mode for testing
    """

    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str = ""
    factory_name: str = ""
    use_default_cred: bool = False
    mock_mode: bool = False
    api_version: str = "2018-06-01"
    retry_total: int = 3
    timeout_seconds: int = 300
    tags: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_environment(cls) -> "ADFConfig":
        """
        Create ADFConfig from environment variables.

        Required env vars (unless MOCK_ADF=true):
            AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
            AZURE_SUBSCRIPTION_ID

        Optional env vars:
            ADF_RESOURCE_GROUP, ADF_FACTORY_NAME, MOCK_ADF
        """
        mock_mode = os.getenv("MOCK_ADF", "false").lower() in ("true", "1", "yes")

        tenant_id = os.getenv("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000000")
        client_id = os.getenv("AZURE_CLIENT_ID", "00000000-0000-0000-0000-000000000000")
        client_secret = os.getenv("AZURE_CLIENT_SECRET", "mock-secret-placeholder")
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000000")

        if not mock_mode:
            required_vars = [
                "AZURE_TENANT_ID",
                "AZURE_CLIENT_ID",
                "AZURE_CLIENT_SECRET",
                "AZURE_SUBSCRIPTION_ID",
            ]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                logger.warning(
                    "Missing environment variables: %s. Enabling mock mode for ADFClient.",
                    ", ".join(missing),
                )
                mock_mode = True

        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            subscription_id=subscription_id,
            resource_group=os.getenv("ADF_RESOURCE_GROUP", "rg-data-engineering-dev"),
            factory_name=os.getenv("ADF_FACTORY_NAME", "adf-data-engineering-dev"),
            mock_mode=mock_mode,
        )


class ADFClient:
    """
    Azure Data Factory Management Client wrapper with Azure Service Principal authentication
    and fallback mocking.
    """

    def __init__(self, config: ADFConfig) -> None:
        """
        Initialize ADFClient with configuration.

        Args:
            config: ADFConfig dataclass with Azure credentials and settings
        """
        self.config = config
        self._credential: Optional[Any] = None
        self._adf_client: Optional[Any] = None
        self._resource_client: Optional[Any] = None

        logger.info(
            "ADFClient initialized | subscription=%s | factory=%s | mock_mode=%s",
            config.subscription_id[:8] + "...",
            config.factory_name or "not-set",
            config.mock_mode,
        )

    @classmethod
    def from_environment(cls) -> "ADFClient":
        """
        Create ADFClient from environment variables.
        """
        config = ADFConfig.from_environment()
        return cls(config)

    @classmethod
    def from_default_credential(
        cls, subscription_id: str, resource_group: str = "", factory_name: str = ""
    ) -> "ADFClient":
        """
        Create ADFClient using DefaultAzureCredential.
        """
        config = ADFConfig(
            tenant_id="",
            client_id="",
            client_secret="",
            subscription_id=subscription_id,
            resource_group=resource_group,
            factory_name=factory_name,
            use_default_cred=True,
        )
        return cls(config)

    def _get_credential(self) -> Any:
        """
        Get or create Azure credential object.
        """
        if self._credential is None:
            if self.config.mock_mode:
                logger.info("Mock mode enabled: returning MockCredential")
                self._credential = MagicMock(name="MockCredential")
            elif self.config.use_default_cred:
                logger.debug("Using DefaultAzureCredential")
                self._credential = DefaultAzureCredential()
            else:
                logger.debug("Using ClientSecretCredential")
                self._credential = ClientSecretCredential(
                    tenant_id=self.config.tenant_id,
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                )
        return self._credential

    def get_management_client(self) -> Any:
        """
        Get the DataFactoryManagementClient or mock client.
        """
        if self._adf_client is None:
            if self.config.mock_mode:
                logger.info("Initializing Mock DataFactoryManagementClient")
                mock_client = MagicMock(name="DataFactoryManagementClient")
                
                # Mock factory create_or_update response
                mock_factory = MagicMock()
                mock_factory.name = self.config.factory_name or "adf-mock-factory"
                mock_factory.id = f"/subscriptions/{self.config.subscription_id}/resourceGroups/{self.config.resource_group}/providers/Microsoft.DataFactory/factories/{mock_factory.name}"
                mock_factory.location = "eastus"
                mock_factory.provisioning_state = "Succeeded"
                mock_factory.tags = {"env": "dev"}
                mock_factory.e_tag = "mock-etag-12345"
                mock_factory.create_time = "2026-01-01T00:00:00Z"
                mock_factory.repo_configuration = None

                mock_client.factories.create_or_update.return_value = mock_factory
                mock_client.factories.get.return_value = mock_factory
                mock_client.factories.list.return_value = [mock_factory]
                mock_client.factories.list_by_resource_group.return_value = [mock_factory]

                self._adf_client = mock_client
            else:
                credential = self._get_credential()
                self._adf_client = DataFactoryManagementClient(
                    credential=credential,
                    subscription_id=self.config.subscription_id,
                )
                logger.info(
                    "DataFactoryManagementClient created for subscription=%s",
                    self.config.subscription_id[:8] + "...",
                )
        return self._adf_client

    def get_resource_client(self) -> Any:
        """
        Get the ResourceManagementClient or mock client.
        """
        if self._resource_client is None:
            if self.config.mock_mode:
                self._resource_client = MagicMock(name="ResourceManagementClient")
            else:
                credential = self._get_credential()
                self._resource_client = ResourceManagementClient(
                    credential=credential,
                    subscription_id=self.config.subscription_id,
                )
        return self._resource_client

    def create_data_factory(
        self,
        resource_group: str,
        factory_name: str,
        location: str = "eastus",
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create or update an Azure Data Factory instance.
        """
        adf = self.get_management_client()
        tags = tags or {"project": "data-engineering-diaries", "managed-by": "python-sdk"}

        logger.info("Creating Data Factory: %s in %s/%s", factory_name, resource_group, location)

        if self.config.mock_mode:
            return {
                "name": factory_name,
                "id": f"/subscriptions/{self.config.subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.DataFactory/factories/{factory_name}",
                "location": location,
                "provisioning_state": "Succeeded",
                "tags": tags,
            }

        factory = adf.factories.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            factory={
                "location": location,
                "tags": tags,
                "properties": {
                    "publicNetworkAccess": "Enabled",
                },
            },
        )

        logger.info(
            "Data Factory created | name=%s | state=%s | id=%s",
            factory.name,
            factory.provisioning_state,
            factory.id,
        )

        return {
            "name": factory.name,
            "id": factory.id,
            "location": factory.location,
            "provisioning_state": factory.provisioning_state,
            "tags": factory.tags,
        }

    def get_data_factory(self, resource_group: str, factory_name: str) -> Dict[str, Any]:
        """
        Get an existing Data Factory's details.
        """
        adf = self.get_management_client()
        if self.config.mock_mode:
            return {
                "name": factory_name,
                "id": f"/subscriptions/{self.config.subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.DataFactory/factories/{factory_name}",
                "location": "eastus",
                "provisioning_state": "Succeeded",
                "create_time": "2026-01-01T00:00:00Z",
                "etag": "mock-etag-123",
            }

        factory = adf.factories.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
        )

        return {
            "name": factory.name,
            "id": factory.id,
            "location": factory.location,
            "provisioning_state": factory.provisioning_state,
            "create_time": str(factory.create_time),
            "etag": factory.e_tag,
        }

    def list_data_factories(self, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List Data Factory instances.
        """
        adf = self.get_management_client()
        if self.config.mock_mode:
            return [
                {
                    "name": self.config.factory_name or "adf-mock-factory",
                    "id": f"/subscriptions/{self.config.subscription_id}/resourceGroups/{resource_group or 'default-rg'}/providers/Microsoft.DataFactory/factories/adf-mock-factory",
                    "location": "eastus",
                    "provisioning_state": "Succeeded",
                }
            ]

        if resource_group:
            factories = adf.factories.list_by_resource_group(resource_group)
        else:
            factories = adf.factories.list()

        result = []
        for factory in factories:
            result.append({
                "name": factory.name,
                "id": factory.id,
                "location": factory.location,
                "provisioning_state": factory.provisioning_state,
            })

        logger.info("Listed %d Data Factories", len(result))
        return result

    def delete_data_factory(self, resource_group: str, factory_name: str) -> None:
        """
        Delete a Data Factory.
        """
        adf = self.get_management_client()
        logger.warning("DELETING Data Factory: %s/%s", resource_group, factory_name)

        if not self.config.mock_mode:
            adf.factories.delete(
                resource_group_name=resource_group,
                factory_name=factory_name,
            )

        logger.warning("Data Factory deleted: %s", factory_name)

    def get_factory_git_info(self, resource_group: str, factory_name: str) -> Dict[str, Any]:
        """
        Get Git integration configuration for a factory.
        """
        if self.config.mock_mode:
            return {
                "git_configured": True,
                "type": "FactoryGitHubConfiguration",
                "account_name": "sathiyamurthy",
                "repository_name": "production-data-engineering-projects",
                "collaboration_branch": "main",
                "root_folder": "/projects/13_azure_data_factory",
            }

        factory = self.get_management_client().factories.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
        )

        repo_config = factory.repo_configuration
        if repo_config is None:
            return {"git_configured": False}

        return {
            "git_configured": True,
            "type": type(repo_config).__name__,
            "account_name": getattr(repo_config, "account_name", None),
            "repository_name": getattr(repo_config, "repository_name", None),
            "collaboration_branch": getattr(repo_config, "collaboration_branch", None),
            "root_folder": getattr(repo_config, "root_folder", None),
        }

    def __repr__(self) -> str:
        return (
            f"ADFClient(subscription={self.config.subscription_id[:8]}..., "
            f"factory={self.config.factory_name!r}, mock={self.config.mock_mode})"
        )
