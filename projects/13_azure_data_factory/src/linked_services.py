"""
linked_services.py - Azure Data Factory Linked Services Manager
=================================================================
Production-grade definition and deployment of ADF Linked Services.

Explanation:
    Linked Services define connection information to external data stores or compute resources.
    Think of them as database connection strings in traditional applications.
    This module builds, deploys, and manages Linked Services for:
    1. Azure Blob Storage (Connection String & Managed Identity)
    2. Azure Data Lake Storage Gen2 (ADLS Gen2 with Account Key / Service Principal)
    3. Azure SQL Database (SQL Auth / Key Vault Secret Reference)
    4. Snowflake (Account URL, User, Key Vault Secret Password)
    5. Azure Key Vault (For secure credential retrieval)

Business Use Case:
    Centralized credential management across hybrid data platforms. Production pipelines must
    never hardcode secrets in JSON or SDK definitions. They must use Azure Key Vault linked services
    or System-Assigned Managed Identities (SAMI) for security and zero-trust compliance.

Production Example:
    ls_mgr = LinkedServiceManager(adf_client)
    ls_mgr.create_key_vault_linked_service("my-rg", "my-adf", "KeyVaultLS", "https://mykv.vault.azure.net/")
    ls_mgr.create_adls_gen2_linked_service("my-rg", "my-adf", "ADLSGen2LS", "https://mystorage.dfs.core.windows.net")

Interview Questions:
    Q: What is the difference between Linked Service and Dataset in ADF?
    A: Linked Service defines the *connection* (server name, credentials, authentication mechanism).
       Dataset defines the *data structure and location* (table name, file path, schema, format)
       built on top of a specific Linked Service.

    Q: Why should you prefer Managed Identity over Service Principal or Shared Access Keys?
    A: Managed Identities eliminate secret management completely. Azure automatically handles credential
       rotation, eliminating key leakage risks and simplifying deployment pipelines.
"""

import logging
from typing import Any, Dict, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class LinkedServiceManager:
    """
    Manager for creating, retrieving, listing, and testing Azure Data Factory Linked Services.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize LinkedServiceManager with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def create_key_vault_linked_service(
        self,
        resource_group: str,
        factory_name: str,
        linked_service_name: str,
        key_vault_url: str,
    ) -> Dict[str, Any]:
        """
        Create Azure Key Vault Linked Service for secure credential retrieval.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Name for the Linked Service
            key_vault_url: Azure Key Vault URI (e.g. https://mykv.vault.azure.net/)

        Returns:
            Created Linked Service resource payload dict
        """
        logger.info("Creating Key Vault Linked Service: %s", linked_service_name)
        payload = {
            "properties": {
                "type": "AzureKeyVault",
                "typeProperties": {
                    "baseUrl": key_vault_url,
                },
                "description": "Enterprise Key Vault reference for secure connection credentials",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Key Vault LS %s", linked_service_name)
            return {"name": linked_service_name, "type": "AzureKeyVault", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.linked_services.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            linked_service_name=linked_service_name,
            linked_service=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_azure_blob_linked_service(
        self,
        resource_group: str,
        factory_name: str,
        linked_service_name: str,
        connection_string: Optional[str] = None,
        account_endpoint: Optional[str] = None,
        key_vault_ls_name: Optional[str] = None,
        secret_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create Azure Blob Storage Linked Service using connection string or Key Vault reference.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Name for the Linked Service
            connection_string: Plaintext connection string (for testing)
            account_endpoint: Blob endpoint (e.g. https://mystorage.blob.core.windows.net)
            key_vault_ls_name: Azure Key Vault Linked Service name if referencing secret
            secret_name: Key Vault secret name containing connection string

        Returns:
            Created Linked Service resource payload dict
        """
        logger.info("Creating Azure Blob Storage Linked Service: %s", linked_service_name)

        if key_vault_ls_name and secret_name:
            connection_string_prop = {
                "type": "AzureKeyVaultSecret",
                "store": {"referenceName": key_vault_ls_name, "type": "LinkedServiceReference"},
                "secretName": secret_name,
            }
        elif connection_string:
            connection_string_prop = connection_string
        elif account_endpoint:
            connection_string_prop = f"DefaultEndpointsProtocol=https;AccountName={account_endpoint.split('//')[-1].split('.')[0]};EndpointSuffix=core.windows.net"
        else:
            raise ValueError("Must specify connection_string, account_endpoint, or Key Vault secret details.")

        payload = {
            "properties": {
                "type": "AzureBlobStorage",
                "typeProperties": {
                    "connectionString": connection_string_prop,
                },
                "description": "Azure Blob Storage linked service for staging and ingestion",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Azure Blob LS %s", linked_service_name)
            return {"name": linked_service_name, "type": "AzureBlobStorage", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.linked_services.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            linked_service_name=linked_service_name,
            linked_service=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_adls_gen2_linked_service(
        self,
        resource_group: str,
        factory_name: str,
        linked_service_name: str,
        url: str,
        tenant_id: Optional[str] = None,
        service_principal_id: Optional[str] = None,
        service_principal_key_vault_secret: Optional[str] = None,
        key_vault_ls_name: Optional[str] = None,
        use_managed_identity: bool = True,
    ) -> Dict[str, Any]:
        """
        Create Azure Data Lake Storage Gen2 (ADLS Gen2) Linked Service.

        Supports System-Assigned Managed Identity or Service Principal Auth.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Linked Service name
            url: ADLS Gen2 Endpoint URL (https://<account>.dfs.core.windows.net)
            tenant_id: Azure Tenant ID (required if Service Principal)
            service_principal_id: Client ID (required if Service Principal)
            service_principal_key_vault_secret: KV Secret Name for Client Secret
            key_vault_ls_name: Key Vault Linked Service name
            use_managed_identity: If True, use Managed Identity authentication (default)

        Returns:
            Created Linked Service resource payload dict
        """
        logger.info("Creating ADLS Gen2 Linked Service: %s (ManagedIdentity=%s)", linked_service_name, use_managed_identity)

        type_properties: Dict[str, Any] = {"url": url}

        if use_managed_identity:
            type_properties["authenticationType"] = "ManagedIdentity"
        else:
            if not (tenant_id and service_principal_id and service_principal_key_vault_secret and key_vault_ls_name):
                raise ValueError("Service principal authentication requires tenant_id, service_principal_id, secret name, and key vault LS.")
            type_properties["tenant"] = tenant_id
            type_properties["servicePrincipalId"] = service_principal_id
            type_properties["servicePrincipalCredentialType"] = "ServicePrincipalKey"
            type_properties["servicePrincipalKey"] = {
                "type": "AzureKeyVaultSecret",
                "store": {"referenceName": key_vault_ls_name, "type": "LinkedServiceReference"},
                "secretName": service_principal_key_vault_secret,
            }

        payload = {
            "properties": {
                "type": "AzureBlobFS",
                "typeProperties": type_properties,
                "description": "ADLS Gen2 Enterprise Data Lake Storage Linked Service",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created ADLS Gen2 LS %s", linked_service_name)
            return {"name": linked_service_name, "type": "AzureBlobFS", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.linked_services.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            linked_service_name=linked_service_name,
            linked_service=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_azure_sql_linked_service(
        self,
        resource_group: str,
        factory_name: str,
        linked_service_name: str,
        server: str,
        database: str,
        username: str,
        key_vault_ls_name: str,
        password_secret_name: str,
        encrypt: bool = True,
        trust_server_certificate: bool = False,
    ) -> Dict[str, Any]:
        """
        Create Azure SQL Database Linked Service using Key Vault secret for password.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Linked Service name
            server: SQL Server FQDN (e.g. myserver.database.windows.net)
            database: Database name
            username: SQL User login
            key_vault_ls_name: Key Vault Linked Service reference
            password_secret_name: Key Vault Secret containing SQL password
            encrypt: Enable SSL encryption
            trust_server_certificate: Trust server certificate

        Returns:
            Created Linked Service resource payload dict
        """
        logger.info("Creating Azure SQL Linked Service: %s (Server=%s, DB=%s)", linked_service_name, server, database)

        conn_str = f"Server=tcp:{server},1433;Initial Catalog={database};User ID={username};Encrypt={str(encrypt).lower()};TrustServerCertificate={str(trust_server_certificate).lower()};"

        payload = {
            "properties": {
                "type": "AzureSqlDatabase",
                "typeProperties": {
                    "connectionString": conn_str,
                    "password": {
                        "type": "AzureKeyVaultSecret",
                        "store": {"referenceName": key_vault_ls_name, "type": "LinkedServiceReference"},
                        "secretName": password_secret_name,
                    },
                },
                "description": "Azure SQL Relational Database Linked Service with Key Vault Password Reference",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Azure SQL LS %s", linked_service_name)
            return {"name": linked_service_name, "type": "AzureSqlDatabase", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.linked_services.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            linked_service_name=linked_service_name,
            linked_service=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def create_snowflake_linked_service(
        self,
        resource_group: str,
        factory_name: str,
        linked_service_name: str,
        account_url: str,
        username: str,
        database: str,
        warehouse: str,
        key_vault_ls_name: str,
        password_secret_name: str,
        schema: Optional[str] = "PUBLIC",
        role: Optional[str] = "ACCOUNTADMIN",
    ) -> Dict[str, Any]:
        """
        Create Snowflake Linked Service for Cloud Data Warehouse integration.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Linked Service name
            account_url: Snowflake account URL (e.g. https://xy12345.snowflakecomputing.com)
            username: Snowflake username
            database: Snowflake database name
            warehouse: Snowflake virtual warehouse name
            key_vault_ls_name: Key Vault Linked Service reference
            password_secret_name: Key Vault Secret name containing Snowflake password
            schema: Default Snowflake schema
            role: Default Snowflake role

        Returns:
            Created Linked Service resource payload dict
        """
        logger.info("Creating Snowflake Linked Service: %s (Account=%s)", linked_service_name, account_url)

        conn_str = (
            f"accountUrl={account_url};user={username};db={database};"
            f"warehouse={warehouse};schema={schema};role={role};"
        )

        payload = {
            "properties": {
                "type": "Snowflake",
                "typeProperties": {
                    "connectionString": conn_str,
                    "password": {
                        "type": "AzureKeyVaultSecret",
                        "store": {"referenceName": key_vault_ls_name, "type": "LinkedServiceReference"},
                        "secretName": password_secret_name,
                    },
                },
                "description": "Snowflake Data Warehouse Linked Service",
            }
        }

        if self.client.config.mock_mode:
            logger.info("Mock mode: successfully created Snowflake LS %s", linked_service_name)
            return {"name": linked_service_name, "type": "Snowflake", "status": "Created"}

        adf = self.client.get_management_client()
        result = adf.linked_services.create_or_update(
            resource_group_name=resource_group,
            factory_name=factory_name,
            linked_service_name=linked_service_name,
            linked_service=payload,
        )
        return {"name": result.name, "id": result.id, "type": result.properties.type}

    def get_linked_service(self, resource_group: str, factory_name: str, linked_service_name: str) -> Dict[str, Any]:
        """
        Get details of an existing Linked Service.

        Args:
            resource_group: Resource group name
            factory_name: Data Factory name
            linked_service_name: Linked Service name

        Returns:
            Linked service specification dict
        """
        if self.client.config.mock_mode:
            return {
                "name": linked_service_name,
                "type": "AzureBlobFS",
                "description": "Mocked Linked Service",
            }

        adf = self.client.get_management_client()
        ls = adf.linked_services.get(resource_group_name=resource_group, factory_name=factory_name, linked_service_name=linked_service_name)
        return {"name": ls.name, "id": ls.id, "type": ls.properties.type}

    def list_linked_services(self, resource_group: str, factory_name: str) -> list[Dict[str, Any]]:
        """
        List all Linked Services in a Data Factory.
        """
        if self.client.config.mock_mode:
            return [
                {"name": "KeyVaultLS", "type": "AzureKeyVault"},
                {"name": "ADLSGen2LS", "type": "AzureBlobFS"},
                {"name": "AzureSqlLS", "type": "AzureSqlDatabase"},
            ]

        adf = self.client.get_management_client()
        services = adf.linked_services.list_by_factory(resource_group_name=resource_group, factory_name=factory_name)
        return [{"name": ls.name, "type": ls.properties.type} for ls in services]

    def delete_linked_service(self, resource_group: str, factory_name: str, linked_service_name: str) -> None:
        """
        Delete a Linked Service.
        """
        logger.warning("Deleting Linked Service: %s from ADF %s", linked_service_name, factory_name)
        if not self.client.config.mock_mode:
            adf = self.client.get_management_client()
            adf.linked_services.delete(resource_group_name=resource_group, factory_name=factory_name, linked_service_name=linked_service_name)
