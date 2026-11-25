"""
Azure Key Vault Integration with Databricks Secret Scopes
==========================================================
Production patterns for managing secrets in Azure Databricks using
Azure Key Vault-backed secret scopes.

Business Use Case:
    Enterprise Databricks workloads require secure secret management.
    Instead of hardcoding credentials or using environment variables,
    all secrets (connection strings, passwords, API keys, storage keys)
    are stored in Azure Key Vault and accessed through Databricks
    secret scopes — eliminating secrets from code, notebooks, and logs.

Architecture:
    Azure Key Vault
    └── Databricks Secret Scope (AKV-backed)
        ├── db-connection-string  (SQL passwords)
        ├── sp-client-secret      (Service principal creds)
        ├── adls-access-key       (Storage access keys)
        ├── synapse-jdbc-url      (Synapse connection)
        └── api-keys              (External APIs)

    Access Pattern:
        dbutils.secrets.get(scope="kv-prod-scope", key="sp-client-secret")

Secret Scope Types:
    1. Azure Key Vault-backed  → Recommended. Secrets stored in AKV,
                                  Databricks reads directly via AAD.
    2. Databricks-managed      → Secrets encrypted in Databricks metadata.
                                  No external dependency but less auditable.

Production Best Practices:
    - One Key Vault per environment (dev, staging, prod)
    - Use RBAC on Key Vault (avoid old Access Policies model)
    - Assign 'Key Vault Secrets User' role to Databricks workspace MSI
    - Rotate secrets without code changes using Key Vault versioning
    - Enable Key Vault soft delete and purge protection
    - Monitor secret access via Key Vault diagnostic logs → Log Analytics

Interview Questions:
    Q: How do you prevent secrets from appearing in Databricks logs?
    A: Databricks automatically redacts [REDACTED] when secrets retrieved
       via dbutils.secrets.get() are printed. However, developers must
       not concatenate secrets into user-defined strings and print them.

    Q: What is the difference between AKV-backed and Databricks-managed scopes?
    A: AKV-backed scopes store secrets in Azure Key Vault. All reads go
       through AAD authentication, providing full audit trail in AKV logs.
       Databricks-managed scopes encrypt and store in Databricks internal
       store — no external dependency but less audit transparency.

    Q: How do you rotate a secret without pipeline downtime?
    A: Update the secret in Key Vault. All subsequent dbutils.secrets.get()
       calls will return the new value automatically. No cluster restart
       or code change needed. For JDBC connections, new connections will
       pick up the new secret.

Author:  Sathiya Murthy — Data Engineering Diaries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SecretScopeConfig:
    """
    Configuration for a Databricks secret scope.

    Attributes:
        scope_name:      Databricks secret scope name
        akv_dns_name:    Azure Key Vault DNS name (for AKV-backed scopes)
        akv_resource_id: Azure Key Vault ARM resource ID (for AKV-backed)
        scope_type:      'akv_backed' or 'databricks_managed'
    """
    scope_name: str
    akv_dns_name: Optional[str] = None
    akv_resource_id: Optional[str] = None
    scope_type: str = "akv_backed"

    @property
    def akv_url(self) -> Optional[str]:
        """Return the Key Vault URL."""
        if self.akv_dns_name:
            return f"https://{self.akv_dns_name}.vault.azure.net"
        return None


@dataclass
class SecretReference:
    """
    A reference to a secret in a Databricks secret scope.

    Use this to pass secret references without ever materializing
    the secret value until needed.
    """
    scope: str
    key: str
    description: str = ""

    def __repr__(self) -> str:
        """Never expose secret value in repr."""
        return f"SecretReference(scope={self.scope!r}, key={self.key!r})"


# ---------------------------------------------------------------------------
# Azure Key Vault Manager
# ---------------------------------------------------------------------------

class AzureKeyVaultManager:
    """
    Production Azure Key Vault integration for Azure Databricks.

    Manages secret scope creation, secret retrieval, and provides
    safe wrappers for common credential patterns used in data pipelines.

    Example:
        >>> kv_config = SecretScopeConfig(
        ...     scope_name="kv-prod-scope",
        ...     akv_dns_name="mycompany-kv-prod",
        ...     akv_resource_id=(
        ...         "/subscriptions/<sub-id>/resourceGroups/<rg>/providers"
        ...         "/Microsoft.KeyVault/vaults/mycompany-kv-prod"
        ...     ),
        ... )
        >>> kv_manager = AzureKeyVaultManager(kv_config, dbutils=dbutils)
        >>> sp_secret = kv_manager.get_secret("sp-client-secret")
        >>> jdbc_url = kv_manager.get_jdbc_connection_string("synapse")
    """

    def __init__(
        self,
        config: SecretScopeConfig,
        dbutils: Optional[Any] = None,
    ) -> None:
        self.config = config
        self._dbutils = dbutils
        logger.info(
            "AzureKeyVaultManager initialized | scope=%s | type=%s",
            config.scope_name,
            config.scope_type,
        )

    # ------------------------------------------------------------------
    # Core Secret Operations
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str:
        """
        Retrieve a secret value from the configured scope.

        In Databricks notebooks, this calls dbutils.secrets.get().
        The returned value is redacted if accidentally printed.

        Args:
            key: Secret key name in the scope

        Returns:
            str: The secret value (Databricks-redacted in logs)

        Raises:
            ValueError: If dbutils is not available
            Exception:  If secret key does not exist in scope
        """
        if self._dbutils is None:
            raise ValueError(
                "dbutils is not set. Pass dbutils when initializing "
                "AzureKeyVaultManager in a Databricks notebook/job."
            )
        logger.debug("Retrieving secret: scope=%s, key=%s", self.config.scope_name, key)
        return self._dbutils.secrets.get(
            scope=self.config.scope_name, key=key
        )

    def get_secret_safe(self, key: str, default: str = "") -> str:
        """
        Retrieve a secret with a fallback default (for optional configs).

        Warning: Only use default="" for non-sensitive optional configs.
        Never provide a default for security-critical secrets.

        Args:
            key:     Secret key name
            default: Default value if secret not found

        Returns:
            str: Secret value or default
        """
        try:
            return self.get_secret(key)
        except Exception as exc:
            logger.warning("Secret not found: key=%s, using default. Error: %s", key, exc)
            return default

    def list_secrets(self) -> List[Dict[str, str]]:
        """
        List all secret keys in the scope (values are not returned).

        Returns:
            List of dicts with 'key' and 'lastChangedDate'

        Note:
            For AKV-backed scopes, this lists secrets visible to the
            Databricks workspace MSI/SP based on its Key Vault permissions.
        """
        if self._dbutils is None:
            raise ValueError("dbutils not available")
        secrets = self._dbutils.secrets.list(self.config.scope_name)
        logger.info(
            "Listed %d secrets in scope: %s", len(secrets), self.config.scope_name
        )
        return [{"key": s.key, "lastChangedDate": str(s.lastChangedDate)} for s in secrets]

    # ------------------------------------------------------------------
    # Credential Bundle Helpers
    # ------------------------------------------------------------------

    def get_service_principal_credentials(
        self,
        tenant_key: str = "sp-tenant-id",
        client_id_key: str = "sp-client-id",
        client_secret_key: str = "sp-client-secret",
    ) -> Dict[str, str]:
        """
        Retrieve a complete service principal credential bundle.

        Standard Key Vault secret naming convention:
            sp-tenant-id      → Azure AD tenant ID
            sp-client-id      → Application (client) ID
            sp-client-secret  → Client secret value

        Returns:
            Dict with keys: tenant_id, client_id, client_secret
        """
        logger.info(
            "Retrieving service principal credentials from scope: %s",
            self.config.scope_name,
        )
        return {
            "tenant_id": self.get_secret(tenant_key),
            "client_id": self.get_secret(client_id_key),
            "client_secret": self.get_secret(client_secret_key),
        }

    def get_jdbc_connection_string(
        self,
        service: str,
        host_key: Optional[str] = None,
        password_key: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        """
        Build a JDBC connection string from Key Vault secrets.

        Supports: Azure Synapse Analytics, Azure SQL, PostgreSQL

        Args:
            service:      Service type: 'synapse', 'azuresql', 'postgresql'
            host_key:     KV key for the server hostname
            password_key: KV key for the database password
            database:     Database name (or retrieve from KV)
            username:     Database username (or retrieve from KV)

        Returns:
            str: JDBC connection string with embedded credentials

        Example:
            >>> jdbc = kv.get_jdbc_connection_string(
            ...     service="synapse",
            ...     host_key="synapse-server-name",
            ...     password_key="synapse-admin-password",
            ...     database="analytics_dw",
            ...     username="svc_databricks",
            ... )
        """
        # Resolve defaults based on service naming convention
        host_key = host_key or f"{service}-server-name"
        password_key = password_key or f"{service}-password"
        username_key = f"{service}-username"

        server = self.get_secret(host_key)
        password = self.get_secret(password_key)
        user = username or self.get_secret_safe(username_key, "svc_databricks")

        if service == "synapse":
            jdbc_url = (
                f"jdbc:sqlserver://{server}.sql.azuresynapse.net:1433;"
                f"database={database or 'analytics_dw'};"
                f"user={user}@{server};password={password};"
                "encrypt=true;trustServerCertificate=false;"
                "hostNameInCertificate=*.sql.azuresynapse.net;loginTimeout=30;"
            )
        elif service == "azuresql":
            jdbc_url = (
                f"jdbc:sqlserver://{server}.database.windows.net:1433;"
                f"database={database or 'master'};"
                f"user={user}@{server};password={password};"
                "encrypt=true;trustServerCertificate=false;"
                "hostNameInCertificate=*.database.windows.net;loginTimeout=30;"
            )
        elif service == "postgresql":
            jdbc_url = (
                f"jdbc:postgresql://{server}.postgres.database.azure.com:5432/"
                f"{database or 'postgres'}?"
                f"user={user}&password={password}&sslmode=require"
            )
        else:
            raise ValueError(f"Unsupported service: {service}. Use: synapse, azuresql, postgresql")

        logger.info("Built JDBC connection string for service: %s", service)
        return jdbc_url

    def get_storage_account_key(
        self, storage_account_name: str, key_name: Optional[str] = None
    ) -> str:
        """
        Retrieve ADLS/Blob storage account key from Key Vault.

        Naming convention: '{storage-account-name}-access-key'

        Args:
            storage_account_name: Storage account name
            key_name:             Override KV key name

        Returns:
            str: Storage account access key
        """
        key = key_name or f"{storage_account_name}-access-key"
        logger.info("Retrieving storage key for account: %s", storage_account_name)
        return self.get_secret(key)

    def get_event_hub_connection_string(
        self, namespace: str, policy_key: Optional[str] = None
    ) -> str:
        """
        Retrieve Event Hub connection string for streaming pipelines.

        Args:
            namespace:   Event Hub namespace name
            policy_key:  KV key name (default: '{namespace}-connection-string')

        Returns:
            str: Event Hub connection string
        """
        key = policy_key or f"{namespace}-connection-string"
        logger.info("Retrieving Event Hub connection string for: %s", namespace)
        return self.get_secret(key)

    # ------------------------------------------------------------------
    # Secret Scope Management (Databricks REST API)
    # ------------------------------------------------------------------

    @staticmethod
    def get_scope_creation_instructions(
        config: SecretScopeConfig,
    ) -> Dict[str, Any]:
        """
        Return instructions for creating a Databricks secret scope.

        This method does NOT call the API directly. It returns the
        configuration payload for use with the Databricks REST API or CLI.

        AKV-backed scope requires:
            - Key Vault URI
            - Key Vault ARM resource ID
            - Databricks workspace AAD application must have
              'Key Vault Secrets User' RBAC role on the Key Vault

        Returns:
            Dict with scope creation details and curl example
        """
        if config.scope_type == "akv_backed":
            payload = {
                "scope": config.scope_name,
                "scope_backend_type": "AZURE_KEYVAULT",
                "backend_azure_keyvault": {
                    "resource_id": config.akv_resource_id,
                    "dns_name": config.akv_url,
                },
                "initial_manage_principal": "users",
            }
            curl_example = (
                f"curl -X POST https://<databricks-workspace-url>/api/2.0/secrets/scopes/create "
                f"-H 'Authorization: Bearer <dapi-token>' "
                f"-H 'Content-Type: application/json' "
                f"-d '{payload}'"
            )
            cli_example = (
                f"databricks secrets create-scope "
                f"--scope {config.scope_name} "
                f"--scope-backend-type AZURE_KEYVAULT "
                f"--resource-id {config.akv_resource_id} "
                f"--dns-name {config.akv_url}"
            )
        else:
            payload = {
                "scope": config.scope_name,
                "initial_manage_principal": "users",
            }
            cli_example = f"databricks secrets create-scope --scope {config.scope_name}"
            curl_example = ""

        return {
            "scope_name": config.scope_name,
            "scope_type": config.scope_type,
            "api_payload": payload,
            "cli_command": cli_example,
            "curl_example": curl_example,
            "notes": [
                "Run CLI command from Azure Cloud Shell or local Azure CLI",
                "Databricks workspace MSI needs 'Key Vault Secrets User' RBAC role",
                "AKV soft-delete must be enabled for AKV-backed scopes",
            ],
        }

    def validate_scope_access(self, test_key: str) -> bool:
        """
        Validate that the secret scope is accessible and test_key exists.

        Use during pipeline startup to fail fast before processing begins.

        Args:
            test_key: A known secret key to validate access

        Returns:
            bool: True if accessible, False otherwise
        """
        try:
            value = self.get_secret(test_key)
            is_valid = bool(value and len(value) > 0)
            logger.info(
                "Secret scope validation: scope=%s, key=%s, valid=%s",
                self.config.scope_name, test_key, is_valid,
            )
            return is_valid
        except Exception as exc:
            logger.error(
                "Secret scope validation FAILED: scope=%s, key=%s, error=%s",
                self.config.scope_name, test_key, exc,
            )
            return False


# ---------------------------------------------------------------------------
# Convenience Builders
# ---------------------------------------------------------------------------

def create_akv_backed_scope_config(
    scope_name: str,
    akv_name: str,
    subscription_id: str,
    resource_group: str,
) -> SecretScopeConfig:
    """
    Build a SecretScopeConfig for an Azure Key Vault-backed scope.

    Args:
        scope_name:       Databricks secret scope name
        akv_name:         Azure Key Vault name (without .vault.azure.net)
        subscription_id:  Azure subscription ID
        resource_group:   Resource group containing the Key Vault

    Returns:
        SecretScopeConfig ready for AKV-backed scope creation
    """
    resource_id = (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.KeyVault/vaults/{akv_name}"
    )
    return SecretScopeConfig(
        scope_name=scope_name,
        akv_dns_name=akv_name,
        akv_resource_id=resource_id,
        scope_type="akv_backed",
    )


# ---------------------------------------------------------------------------
# Secret Reference Pattern (avoid materializing secrets in objects)
# ---------------------------------------------------------------------------

class SecretBundleBuilder:
    """
    Build collections of SecretReference objects for pipeline configs.

    Keeps secret metadata (scope + key name) without ever retrieving
    the actual values — preventing accidental exposure.

    Example:
        >>> builder = SecretBundleBuilder(scope="kv-prod-scope")
        >>> bundle = (
        ...     builder
        ...     .add("tenant_id", "sp-tenant-id")
        ...     .add("client_id", "sp-client-id")
        ...     .add("client_secret", "sp-client-secret")
        ...     .build()
        ... )
        >>> # Pass bundle to pipeline; each component resolves its own secret
    """

    def __init__(self, scope: str) -> None:
        self._scope = scope
        self._refs: Dict[str, SecretReference] = {}

    def add(
        self, name: str, key: str, description: str = ""
    ) -> "SecretBundleBuilder":
        """Add a secret reference to the bundle."""
        self._refs[name] = SecretReference(
            scope=self._scope, key=key, description=description
        )
        return self

    def build(self) -> Dict[str, SecretReference]:
        """Return the completed secret reference bundle."""
        return dict(self._refs)

    def resolve_all(self, dbutils: Any) -> Dict[str, str]:
        """
        Resolve all secret references to actual values.

        Call this only at the point of use, not during config setup.

        Args:
            dbutils: Databricks dbutils object

        Returns:
            Dict of name → secret value
        """
        resolved = {}
        for name, ref in self._refs.items():
            resolved[name] = dbutils.secrets.get(scope=ref.scope, key=ref.key)
        logger.info("Resolved %d secrets from bundle", len(resolved))
        return resolved
