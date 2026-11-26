"""
ADLS Gen2 Integration for Azure Databricks
===========================================
Comprehensive Azure Data Lake Storage Gen2 integration patterns.

Business Use Case:
    Enterprise data lake on ADLS Gen2 serving as the primary storage layer
    for raw, curated, and processed data, accessible from Azure Databricks
    using multiple authentication mechanisms for different deployment scenarios.

Authentication Patterns:
    1. SAS Token           – Quick dev/test access (not recommended for prod)
    2. Service Principal   – Standard enterprise pattern (OAuth 2.0)
    3. Managed Identity    – Best practice for production Databricks on Azure
    4. Access Key          – Legacy, avoid in production

Architecture:
    ADLS Gen2 (Storage Account)
    ├── raw/          (bronze layer)
    ├── curated/      (silver layer)
    └── processed/    (gold layer)

Performance Notes:
    - Use hierarchical namespace (HNS) enabled storage accounts
    - Enable soft delete and versioning for production containers
    - Use Azure Private Endpoints to eliminate public internet traffic
    - Leverage ADLS Gen2 native support for Delta Lake transaction logs

Common Mistakes:
    - Mounting with storage keys (rotated → broken pipelines)
    - Using SAS tokens without expiry management
    - Not setting spark.hadoop configs at cluster init (not job level)
    - Forgetting to set recursive ACLs on directory tree

Interview Questions:
    Q: What is the difference between ADLS Gen1 and Gen2?
    A: Gen2 is built on Azure Blob Storage with hierarchical namespace (HNS).
       It supports POSIX-style ACLs, is cheaper, supports Parquet natively,
       and has better Spark integration. Gen1 is being retired.

    Q: When should you use mounting vs. direct access in Databricks?
    A: Mounting makes paths portable (dbfs:/mnt/...) but secrets leak into
       cluster configs. Direct access with abfss:// is preferred in Unity
       Catalog environments where storage credentials are managed centrally.

    Q: What is abfss:// vs wasbs://?
    A: abfss:// uses the Azure Blob File System (ABFS) driver optimized for
       ADLS Gen2 with HNS. wasbs:// is the legacy Azure Blob Storage driver.
       Always use abfss:// with ADLS Gen2.

Author:  Sathiya Murthy — Data Engineering Diaries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations & Data Classes
# ---------------------------------------------------------------------------

class AuthMethod(Enum):
    """Supported ADLS Gen2 authentication methods."""
    SAS_TOKEN = auto()
    SERVICE_PRINCIPAL = auto()
    MANAGED_IDENTITY = auto()
    ACCESS_KEY = auto()


@dataclass
class ADLSConfig:
    """
    ADLS Gen2 connection configuration.

    Attributes:
        storage_account_name:  Azure storage account name
        container_name:        Container (filesystem) name
        auth_method:           Authentication mechanism to use
        tenant_id:             Azure AD tenant ID (for SP auth)
        client_id:             Service principal / app registration ID
        client_secret:         Service principal secret (from Key Vault)
        sas_token:             SAS token string (for SAS auth)
        access_key:            Storage account access key (legacy)
        mount_point:           DBFS mount point path (e.g. /mnt/datalake)
    """
    storage_account_name: str
    container_name: str
    auth_method: AuthMethod = AuthMethod.SERVICE_PRINCIPAL
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    sas_token: Optional[str] = None
    access_key: Optional[str] = None
    mount_point: str = "/mnt/datalake"

    @property
    def abfss_base_path(self) -> str:
        """Return the abfss:// base path for direct access."""
        return (
            f"abfss://{self.container_name}"
            f"@{self.storage_account_name}.dfs.core.windows.net"
        )

    @property
    def blob_endpoint(self) -> str:
        """Return Azure Blob DFS endpoint."""
        return f"https://{self.storage_account_name}.dfs.core.windows.net"


@dataclass
class MountPointInfo:
    """Represents an existing DBFS mount point."""
    mount_point: str
    source: str
    encryption_type: str = "none"


# ---------------------------------------------------------------------------
# ADLS Gen2 Manager
# ---------------------------------------------------------------------------

class ADLSGen2Manager:
    """
    Production ADLS Gen2 integration manager for Azure Databricks.

    Handles authentication configuration, mount point management, and
    provides utility methods for reading/writing data across storage layers.

    Example:
        >>> config = ADLSConfig(
        ...     storage_account_name="myenterprisedatalake",
        ...     container_name="raw",
        ...     auth_method=AuthMethod.SERVICE_PRINCIPAL,
        ...     tenant_id="<tenant-id>",
        ...     client_id="<client-id>",
        ...     client_secret="<secret-from-key-vault>",
        ... )
        >>> manager = ADLSGen2Manager(config, spark)
        >>> manager.configure_spark_auth()
        >>> df = manager.read_parquet("landing/sales/2024/01/")
    """

    def __init__(self, config: ADLSConfig, spark: Any) -> None:
        self.config = config
        self.spark = spark
        self._mounted: bool = False
        logger.info(
            "ADLSGen2Manager initialized for account=%s, container=%s, auth=%s",
            config.storage_account_name,
            config.container_name,
            config.auth_method.name,
        )

    # ------------------------------------------------------------------
    # Spark Configuration (called at job/notebook startup)
    # ------------------------------------------------------------------

    def configure_spark_auth(self) -> None:
        """
        Set Spark Hadoop configuration for ADLS Gen2 authentication.

        This method configures the Spark session with the appropriate
        Hadoop OAuth / credentials settings for the chosen auth method.
        Should be called once per Spark session before any ADLS operations.

        Auth Method Decision Tree:
            MANAGED_IDENTITY   → Best for production (no secrets to manage)
            SERVICE_PRINCIPAL  → Standard for automation/CI
            SAS_TOKEN          → Dev/testing only, scoped & time-limited
            ACCESS_KEY         → Legacy; avoid rotation headaches
        """
        cfg = self.config
        account = cfg.storage_account_name
        hadoop_conf = self.spark.sparkContext._jsc.hadoopConfiguration()

        if cfg.auth_method == AuthMethod.SERVICE_PRINCIPAL:
            self._configure_service_principal(hadoop_conf, account)

        elif cfg.auth_method == AuthMethod.MANAGED_IDENTITY:
            self._configure_managed_identity(hadoop_conf, account)

        elif cfg.auth_method == AuthMethod.SAS_TOKEN:
            self._configure_sas_token(hadoop_conf, account)

        elif cfg.auth_method == AuthMethod.ACCESS_KEY:
            self._configure_access_key(hadoop_conf, account)

        logger.info(
            "Spark Hadoop configuration set for auth_method=%s",
            cfg.auth_method.name,
        )

    def _configure_service_principal(
        self, hadoop_conf: Any, account: str
    ) -> None:
        """Configure OAuth 2.0 service principal authentication."""
        cfg = self.config
        prefix = f"fs.azure.account"

        # Use OAuth token provider (recommended pattern)
        hadoop_conf.set(
            f"{prefix}.auth.type.{account}.dfs.core.windows.net",
            "OAuth",
        )
        hadoop_conf.set(
            f"{prefix}.oauth.provider.type.{account}.dfs.core.windows.net",
            "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
        )
        hadoop_conf.set(
            f"{prefix}.oauth2.client.id.{account}.dfs.core.windows.net",
            cfg.client_id,
        )
        hadoop_conf.set(
            f"{prefix}.oauth2.client.secret.{account}.dfs.core.windows.net",
            cfg.client_secret,
        )
        hadoop_conf.set(
            f"{prefix}.oauth2.client.endpoint.{account}.dfs.core.windows.net",
            f"https://login.microsoftonline.com/{cfg.tenant_id}/oauth2/token",
        )
        logger.debug("Service principal OAuth configured for account: %s", account)

    def _configure_managed_identity(
        self, hadoop_conf: Any, account: str
    ) -> None:
        """
        Configure Managed Identity authentication (MSI).

        When Databricks is deployed with a User-Assigned Managed Identity
        or using the workspace MSI, no secrets are needed.
        """
        hadoop_conf.set(
            f"fs.azure.account.auth.type.{account}.dfs.core.windows.net",
            "ManagedIdentity",
        )
        # For user-assigned managed identity, set the client ID:
        if self.config.client_id:
            hadoop_conf.set(
                f"fs.azure.account.oauth2.msi.tenant.{account}.dfs.core.windows.net",
                self.config.client_id,
            )
        logger.debug("Managed Identity configured for account: %s", account)

    def _configure_sas_token(self, hadoop_conf: Any, account: str) -> None:
        """Configure SAS token authentication (dev/test only)."""
        hadoop_conf.set(
            f"fs.azure.account.auth.type.{account}.dfs.core.windows.net",
            "SAS",
        )
        hadoop_conf.set(
            f"fs.azure.sas.token.provider.type.{account}.dfs.core.windows.net",
            "org.apache.hadoop.fs.azurebfs.sas.FixedSASTokenProvider",
        )
        hadoop_conf.set(
            f"fs.azure.sas.fixed.token.{account}.dfs.core.windows.net",
            self.config.sas_token,
        )
        logger.warning(
            "SAS token auth configured. Use only for dev/test. "
            "Token expiry will break pipelines silently."
        )

    def _configure_access_key(self, hadoop_conf: Any, account: str) -> None:
        """Configure storage access key (legacy, not recommended)."""
        hadoop_conf.set(
            f"fs.azure.account.key.{account}.dfs.core.windows.net",
            self.config.access_key,
        )
        logger.warning(
            "Access key auth configured. Prefer Service Principal or "
            "Managed Identity for production workloads."
        )

    # ------------------------------------------------------------------
    # Mount Point Management
    # ------------------------------------------------------------------

    def mount(
        self,
        extra_configs: Optional[Dict[str, str]] = None,
        force_remount: bool = False,
    ) -> str:
        """
        Mount ADLS Gen2 container to DBFS using dbutils.

        NOTE: In Unity Catalog environments, mounting is deprecated.
        Use direct abfss:// paths with external locations instead.

        Args:
            extra_configs:  Additional Spark Hadoop configs for this mount
            force_remount:  Unmount existing mount before remounting

        Returns:
            str: The DBFS mount point path

        Raises:
            RuntimeError: If mount operation fails
        """
        mount_point = self.config.mount_point
        source = self.config.abfss_base_path

        # Build configs based on auth method
        configs = self._build_mount_configs()
        if extra_configs:
            configs.update(extra_configs)

        try:
            # Check if already mounted
            if self._is_mounted(mount_point):
                if force_remount:
                    logger.info("Force remounting: unmounting %s first", mount_point)
                    self._unmount(mount_point)
                else:
                    logger.info(
                        "Mount point %s already exists. Skipping.", mount_point
                    )
                    self._mounted = True
                    return mount_point

            # Perform the mount
            # In real Databricks environment, this would be:
            # dbutils.fs.mount(source=source, mount_point=mount_point, extra_configs=configs)
            logger.info(
                "Mounting %s → %s with auth=%s",
                source, mount_point, self.config.auth_method.name,
            )
            self._mounted = True
            logger.info("Mount successful: %s", mount_point)
            return mount_point

        except Exception as exc:
            logger.error("Mount failed for %s: %s", mount_point, exc)
            raise RuntimeError(f"Failed to mount {source} at {mount_point}") from exc

    def _build_mount_configs(self) -> Dict[str, str]:
        """Build the configs dict for dbutils.fs.mount()."""
        cfg = self.config
        account = cfg.storage_account_name

        if cfg.auth_method == AuthMethod.SERVICE_PRINCIPAL:
            return {
                "fs.azure.account.auth.type": "OAuth",
                "fs.azure.account.oauth.provider.type": (
                    "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider"
                ),
                "fs.azure.account.oauth2.client.id": cfg.client_id,
                "fs.azure.account.oauth2.client.secret": cfg.client_secret,
                "fs.azure.account.oauth2.client.endpoint": (
                    f"https://login.microsoftonline.com/{cfg.tenant_id}/oauth2/token"
                ),
            }
        elif cfg.auth_method == AuthMethod.SAS_TOKEN:
            return {
                f"fs.azure.sas.{cfg.container_name}.{account}.blob.core.windows.net": (
                    cfg.sas_token
                )
            }
        elif cfg.auth_method == AuthMethod.ACCESS_KEY:
            return {
                f"fs.azure.account.key.{account}.blob.core.windows.net": cfg.access_key
            }
        else:
            # Managed Identity — no explicit config needed when workspace MSI is used
            return {}

    def _is_mounted(self, mount_point: str) -> bool:
        """Check if mount point already exists in DBFS."""
        # In real Databricks: return any(m.mountPoint == mount_point for m in dbutils.fs.mounts())
        logger.debug("Checking if %s is mounted", mount_point)
        return False  # Simulated: assume not mounted

    def _unmount(self, mount_point: str) -> None:
        """Unmount a DBFS mount point."""
        # In real Databricks: dbutils.fs.unmount(mount_point)
        logger.info("Unmounting %s", mount_point)

    def list_mounts(self) -> List[MountPointInfo]:
        """Return all current DBFS mount points."""
        # In real Databricks: return dbutils.fs.mounts()
        logger.info("Listing all DBFS mount points")
        return []

    # ------------------------------------------------------------------
    # Data Access Patterns
    # ------------------------------------------------------------------

    def get_path(self, relative_path: str, use_mount: bool = False) -> str:
        """
        Resolve an ADLS path, optionally using mount point.

        Args:
            relative_path:  Path relative to container root (e.g. "raw/sales/")
            use_mount:      If True, use DBFS mount path; else use abfss://

        Returns:
            str: Fully qualified path

        Example:
            >>> manager.get_path("raw/sales/2024/", use_mount=False)
            'abfss://raw@mydatalake.dfs.core.windows.net/raw/sales/2024/'
        """
        relative_path = relative_path.lstrip("/")
        if use_mount:
            return f"{self.config.mount_point}/{relative_path}"
        return f"{self.config.abfss_base_path}/{relative_path}"

    def read_parquet(
        self,
        relative_path: str,
        use_mount: bool = False,
        options: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Read Parquet files from ADLS Gen2.

        Args:
            relative_path:  Path to Parquet file(s) or partition directory
            use_mount:      Use mount point path vs. direct abfss://
            options:        Additional Spark reader options

        Returns:
            pyspark.sql.DataFrame
        """
        full_path = self.get_path(relative_path, use_mount)
        logger.info("Reading Parquet from: %s", full_path)
        reader = self.spark.read.format("parquet")
        if options:
            for k, v in options.items():
                reader = reader.option(k, v)
        return reader.load(full_path)

    def read_delta(
        self,
        relative_path: str,
        version: Optional[int] = None,
        timestamp: Optional[str] = None,
        use_mount: bool = False,
    ) -> Any:
        """
        Read Delta table from ADLS Gen2 with optional time travel.

        Args:
            relative_path:  Path to Delta table directory
            version:        Delta version number for time travel
            timestamp:      Timestamp string for time travel (ISO 8601)
            use_mount:      Use mount point path vs. direct abfss://

        Returns:
            pyspark.sql.DataFrame

        Example:
            >>> df = manager.read_delta("silver/customers/", version=5)
        """
        full_path = self.get_path(relative_path, use_mount)
        logger.info("Reading Delta from: %s", full_path)
        reader = self.spark.read.format("delta")

        if version is not None:
            reader = reader.option("versionAsOf", version)
            logger.info("Time travel: version=%d", version)
        elif timestamp is not None:
            reader = reader.option("timestampAsOf", timestamp)
            logger.info("Time travel: timestamp=%s", timestamp)

        return reader.load(full_path)

    def read_csv(
        self,
        relative_path: str,
        schema: Optional[Any] = None,
        options: Optional[Dict[str, str]] = None,
        use_mount: bool = False,
    ) -> Any:
        """
        Read CSV files from ADLS Gen2 with schema enforcement.

        Args:
            relative_path:  Path to CSV file(s)
            schema:         PySpark StructType schema (prevents schema inference cost)
            options:        Spark reader options (header, delimiter, etc.)
            use_mount:      Use mount point path vs. direct abfss://

        Returns:
            pyspark.sql.DataFrame
        """
        full_path = self.get_path(relative_path, use_mount)
        logger.info("Reading CSV from: %s", full_path)

        default_options = {
            "header": "true",
            "inferSchema": "false" if schema else "true",
            "escape": '"',
            "multiLine": "true",
        }
        if options:
            default_options.update(options)

        reader = self.spark.read.format("csv")
        for k, v in default_options.items():
            reader = reader.option(k, v)
        if schema:
            reader = reader.schema(schema)

        return reader.load(full_path)

    def write_delta(
        self,
        df: Any,
        relative_path: str,
        mode: str = "append",
        partition_by: Optional[List[str]] = None,
        merge_schema: bool = False,
        use_mount: bool = False,
        table_properties: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Write DataFrame as Delta table to ADLS Gen2.

        Args:
            df:               PySpark DataFrame to write
            relative_path:    Target path relative to container root
            mode:             Write mode: 'append', 'overwrite', 'error'
            partition_by:     List of partition column names
            merge_schema:     Enable schema evolution (mergeSchema)
            use_mount:        Use mount point path vs. direct abfss://
            table_properties: Delta table properties to set on write

        Production Pattern:
            Always write with Z-ORDER optimization on high-cardinality
            filter columns AFTER the initial write completes.
        """
        full_path = self.get_path(relative_path, use_mount)
        logger.info(
            "Writing Delta to: %s | mode=%s | partition_by=%s",
            full_path, mode, partition_by,
        )

        writer = df.write.format("delta").mode(mode)

        if merge_schema:
            writer = writer.option("mergeSchema", "true")

        if table_properties:
            for k, v in table_properties.items():
                writer = writer.option(k, v)

        if partition_by:
            writer = writer.partitionBy(*partition_by)

        writer.save(full_path)
        logger.info("Delta write completed: %s", full_path)

    def copy_files(
        self,
        source_relative_path: str,
        dest_relative_path: str,
        recursive: bool = True,
    ) -> None:
        """
        Copy files within ADLS using dbutils.fs.cp().

        Useful for archiving raw files after ingestion or
        moving processed files between zones.

        Args:
            source_relative_path:  Source path relative to container
            dest_relative_path:    Destination path relative to container
            recursive:             Copy recursively (for directories)
        """
        src = self.get_path(source_relative_path)
        dst = self.get_path(dest_relative_path)
        logger.info("Copying %s → %s (recursive=%s)", src, dst, recursive)
        # In real Databricks: dbutils.fs.cp(src, dst, recurse=recursive)

    def list_files(self, relative_path: str) -> List[Dict[str, Any]]:
        """
        List files at an ADLS path using dbutils.fs.ls().

        Args:
            relative_path:  Path to list relative to container root

        Returns:
            List of dicts with keys: name, path, size, modificationTime
        """
        full_path = self.get_path(relative_path)
        logger.info("Listing files at: %s", full_path)
        # In real Databricks: return dbutils.fs.ls(full_path)
        return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Return storage statistics for this ADLS container.

        Useful for monitoring container growth and setting alerts.

        Returns:
            Dict with keys: total_files, total_size_gb, last_modified
        """
        logger.info(
            "Fetching storage stats for %s/%s",
            self.config.storage_account_name,
            self.config.container_name,
        )
        return {
            "storage_account": self.config.storage_account_name,
            "container": self.config.container_name,
            "auth_method": self.config.auth_method.name,
            "abfss_base_path": self.config.abfss_base_path,
        }


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def build_service_principal_config(
    storage_account: str,
    container: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    mount_point: str = "/mnt/datalake",
) -> ADLSConfig:
    """
    Factory function for Service Principal ADLS config.

    Secrets should always come from Azure Key Vault via Databricks secret scopes:
        client_secret = dbutils.secrets.get(scope="kv-scope", key="sp-secret")
    """
    return ADLSConfig(
        storage_account_name=storage_account,
        container_name=container,
        auth_method=AuthMethod.SERVICE_PRINCIPAL,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        mount_point=mount_point,
    )


def build_managed_identity_config(
    storage_account: str,
    container: str,
    mount_point: str = "/mnt/datalake",
    user_assigned_identity_client_id: Optional[str] = None,
) -> ADLSConfig:
    """
    Factory function for Managed Identity ADLS config.

    No secrets needed — ideal for production Databricks workspaces
    where MSI is assigned at the workspace or cluster level.
    """
    return ADLSConfig(
        storage_account_name=storage_account,
        container_name=container,
        auth_method=AuthMethod.MANAGED_IDENTITY,
        client_id=user_assigned_identity_client_id,
        mount_point=mount_point,
    )


# ---------------------------------------------------------------------------
# Example: Multi-Layer Data Lake Setup
# ---------------------------------------------------------------------------

def setup_enterprise_data_lake(
    spark: Any,
    storage_account: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
) -> Dict[str, ADLSGen2Manager]:
    """
    Set up a full Bronze / Silver / Gold ADLS data lake structure.

    Returns a dict of layer name → ADLSGen2Manager for each layer.

    Usage:
        layers = setup_enterprise_data_lake(spark, "myentdatalake", ...)
        df_raw = layers["bronze"].read_parquet("landing/crm/contacts/")
        layers["silver"].write_delta(df_clean, "customers/", mode="overwrite")
    """
    layers: Dict[str, ADLSGen2Manager] = {}
    for layer in ("bronze", "silver", "gold"):
        config = build_service_principal_config(
            storage_account=storage_account,
            container=layer,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            mount_point=f"/mnt/{layer}",
        )
        manager = ADLSGen2Manager(config, spark)
        manager.configure_spark_auth()
        layers[layer] = manager
        logger.info("Data lake layer configured: %s → /mnt/%s", layer, layer)

    logger.info(
        "Enterprise data lake setup complete. Layers: %s", list(layers.keys())
    )
    return layers
