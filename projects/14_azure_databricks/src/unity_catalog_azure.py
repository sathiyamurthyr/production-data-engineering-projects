"""
Unity Catalog on Azure Databricks
===================================
Production implementation of Unity Catalog governance for Azure Databricks,
covering external locations, storage credentials, metastore setup, and
data access management patterns.

Business Use Case:
    Enterprise data governance across multiple Databricks workspaces in Azure.
    Unity Catalog provides centralized access control, data lineage, audit
    logs, and a unified namespace (catalog.schema.table) across all workspaces
    in an Azure Databricks account.

Unity Catalog Object Hierarchy:
    Account (Azure Databricks)
    └── Metastore (1 per region, attached to multiple workspaces)
        └── Catalog (maps to ADLS Gen2 container or path)
            └── Schema (database)
                └── Table / View / Volume / Function

Azure-Specific Setup:
    1. Create Azure Databricks Account (account.azuredatabricks.net)
    2. Create Unity Catalog Metastore in the region
    3. Create ADLS Gen2 storage account for metastore root storage
    4. Create Azure Managed Identity for the metastore
    5. Assign 'Storage Blob Data Contributor' on the storage account
    6. Create Access Connector for Azure Databricks
    7. Assign workspaces to the metastore

Key Concepts:
    - Storage Credential: AAD credential (MI or SP) that Unity Catalog
                          uses to authenticate to cloud storage
    - External Location:  Named ADLS path + storage credential combination
                          that defines where data can reside
    - External Table:     Table with data in external location (not managed)
    - Managed Table:      Table with data managed by Unity Catalog storage
    - Volume:             Non-tabular file storage within Unity Catalog

Interview Questions:
    Q: What is the difference between Unity Catalog and Hive Metastore?
    A: Hive Metastore is workspace-local (no cross-workspace sharing), uses
       table ACLs only, and has limited audit. Unity Catalog is account-level
       (shared across workspaces), uses attribute-based access control (ABAC),
       provides full lineage/audit, and supports Delta Sharing and Volumes.

    Q: How many metastores can you have per region?
    A: One metastore per Azure region per Databricks account. All workspaces
       in that region share the same metastore (and thus governance boundary).

    Q: What is an Access Connector for Azure Databricks?
    A: It's an Azure resource that gives Unity Catalog a System-Assigned
       Managed Identity to authenticate to ADLS Gen2 without needing
       service principal secrets or storage access keys.

    Q: How does Unity Catalog handle data deletion?
    A: For managed tables, DROP TABLE deletes the data from cloud storage.
       For external tables, DROP TABLE only removes the metadata — data
       remains in ADLS. This is a critical production consideration.

Author:  Sathiya Murthy — Data Engineering Diaries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MetastoreConfig:
    """
    Unity Catalog Metastore configuration for Azure.

    Attributes:
        metastore_name:        Descriptive name for the metastore
        region:                Azure region (must match workspace region)
        storage_account:       ADLS Gen2 storage account for metastore root
        container:             Container for metastore root storage
        root_path:             Path within container for metastore root
        access_connector_id:   ARM ID of the Access Connector resource
        workspace_ids:         List of Databricks workspace IDs to attach
    """
    metastore_name: str
    region: str
    storage_account: str
    container: str
    root_path: str = "unity-catalog-root"
    access_connector_id: Optional[str] = None
    workspace_ids: List[str] = field(default_factory=list)

    @property
    def root_storage_path(self) -> str:
        """Return the full abfss path for metastore root storage."""
        return (
            f"abfss://{self.container}"
            f"@{self.storage_account}.dfs.core.windows.net"
            f"/{self.root_path}"
        )


@dataclass
class StorageCredentialConfig:
    """
    Storage credential configuration for Unity Catalog.

    Attributes:
        credential_name:       Unique name for the storage credential
        credential_type:       'managed_identity' or 'service_principal'
        access_connector_id:   ARM resource ID of Access Connector (MI auth)
        tenant_id:             Azure AD tenant (SP auth)
        client_id:             Application ID (SP auth) or MI client ID
        client_secret:         SP client secret (SP auth only)
        comment:               Description for governance documentation
    """
    credential_name: str
    credential_type: str = "managed_identity"
    access_connector_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    comment: str = ""


@dataclass
class ExternalLocationConfig:
    """
    External location configuration for Unity Catalog.

    Attributes:
        location_name:      Unique name for the external location
        url:                abfss:// URL of the ADLS path
        credential_name:    Storage credential to use for authentication
        comment:            Description of what data lives here
        read_only:          If True, only SELECT is allowed (no writes)
        skip_validation:    Skip URL/credential validation on creation
    """
    location_name: str
    url: str
    credential_name: str
    comment: str = ""
    read_only: bool = False
    skip_validation: bool = False


@dataclass
class CatalogConfig:
    """
    Unity Catalog catalog configuration.

    Attributes:
        catalog_name:      Name of the catalog (top-level namespace)
        storage_location:  External location URL for managed tables
        comment:           Description of this catalog's purpose
        properties:        Additional catalog properties
    """
    catalog_name: str
    storage_location: Optional[str] = None
    comment: str = ""
    properties: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Unity Catalog Azure Manager
# ---------------------------------------------------------------------------

class UnityCatalogAzureManager:
    """
    Production Unity Catalog management for Azure Databricks.

    Provides SQL generation and management for all Unity Catalog
    objects: metastores, storage credentials, external locations,
    catalogs, schemas, and tables.

    NOTE: Most operations require account-admin or metastore-admin
    privileges and are executed via SQL or the Unity Catalog REST API.

    Example:
        >>> uc = UnityCatalogAzureManager(spark, sql_runner=spark.sql)
        >>> uc.create_storage_credential(cred_config)
        >>> uc.create_external_location(location_config)
        >>> uc.create_catalog(catalog_config)
    """

    def __init__(self, spark: Any, sql_runner: Optional[Any] = None) -> None:
        self.spark = spark
        self._sql = sql_runner or spark.sql
        logger.info("UnityCatalogAzureManager initialized")

    # ------------------------------------------------------------------
    # Storage Credentials
    # ------------------------------------------------------------------

    def create_storage_credential(
        self, config: StorageCredentialConfig, if_not_exists: bool = True
    ) -> None:
        """
        Create a Unity Catalog storage credential.

        Storage credentials authenticate Unity Catalog to ADLS Gen2.
        Managed Identity (Access Connector) is the recommended approach.

        Args:
            config:          StorageCredentialConfig
            if_not_exists:   Skip if credential already exists

        SQL Generated (Managed Identity):
            CREATE STORAGE CREDENTIAL IF NOT EXISTS my_cred
            WITH AZURE_MANAGED_IDENTITY
            (CREDENTIAL '/subscriptions/.../accessConnectors/my-ac')
            COMMENT 'Production ADLS access';

        SQL Generated (Service Principal):
            CREATE STORAGE CREDENTIAL IF NOT EXISTS my_sp_cred
            WITH AZURE_SERVICE_CREDENTIAL
            (DIRECTORY_ID '<tenant>', APPLICATION_ID '<client-id>',
             CLIENT_SECRET '<secret>')
            COMMENT 'SP-based storage access';
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""

        if config.credential_type == "managed_identity":
            sql = f"""
                CREATE STORAGE CREDENTIAL {exists_clause} `{config.credential_name}`
                WITH AZURE_MANAGED_IDENTITY
                (CREDENTIAL '{config.access_connector_id}')
                COMMENT '{config.comment}'
            """
        elif config.credential_type == "service_principal":
            sql = f"""
                CREATE STORAGE CREDENTIAL {exists_clause} `{config.credential_name}`
                WITH AZURE_SERVICE_CREDENTIAL
                (
                    DIRECTORY_ID '{config.tenant_id}',
                    APPLICATION_ID '{config.client_id}',
                    CLIENT_SECRET '{config.client_secret}'
                )
                COMMENT '{config.comment}'
            """
        else:
            raise ValueError(
                f"Unsupported credential_type: {config.credential_type}. "
                "Use 'managed_identity' or 'service_principal'."
            )

        logger.info(
            "Creating storage credential: %s (type=%s)",
            config.credential_name, config.credential_type,
        )
        self._sql(sql.strip())
        logger.info("Storage credential created: %s", config.credential_name)

    def validate_storage_credential(self, credential_name: str) -> bool:
        """
        Validate that a storage credential works correctly.

        Returns:
            bool: True if credential is functional
        """
        try:
            result = self._sql(
                f"VALIDATE STORAGE CREDENTIAL `{credential_name}`"
            )
            logger.info(
                "Storage credential validated: %s", credential_name
            )
            return True
        except Exception as exc:
            logger.error(
                "Storage credential validation failed: %s | %s",
                credential_name, exc,
            )
            return False

    def list_storage_credentials(self) -> Any:
        """List all storage credentials visible to current user."""
        return self._sql("SHOW STORAGE CREDENTIALS")

    # ------------------------------------------------------------------
    # External Locations
    # ------------------------------------------------------------------

    def create_external_location(
        self, config: ExternalLocationConfig, if_not_exists: bool = True
    ) -> None:
        """
        Create a Unity Catalog external location.

        External locations define the mapping between an ADLS path and
        a storage credential. They are the foundation for external tables
        and volumes in Unity Catalog.

        Args:
            config:          ExternalLocationConfig
            if_not_exists:   Skip if location already exists

        Best Practice:
            Create separate external locations for each data zone:
            - raw-bronze-ext-loc   → abfss://bronze@datalake.dfs.core.windows.net/
            - silver-ext-loc       → abfss://silver@datalake.dfs.core.windows.net/
            - gold-ext-loc         → abfss://gold@datalake.dfs.core.windows.net/

        SQL Generated:
            CREATE EXTERNAL LOCATION IF NOT EXISTS `bronze-location`
            URL 'abfss://bronze@mydatalake.dfs.core.windows.net/'
            WITH (STORAGE CREDENTIAL `my_cred`)
            COMMENT 'Bronze raw data layer';
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        read_only_clause = "READ ONLY" if config.read_only else ""
        skip_val_clause = "SKIP VALIDATION" if config.skip_validation else ""

        sql = f"""
            CREATE EXTERNAL LOCATION {exists_clause} `{config.location_name}`
            URL '{config.url}'
            WITH (STORAGE CREDENTIAL `{config.credential_name}`)
            {read_only_clause}
            {skip_val_clause}
            COMMENT '{config.comment}'
        """
        logger.info(
            "Creating external location: %s → %s", config.location_name, config.url
        )
        self._sql(sql.strip())
        logger.info("External location created: %s", config.location_name)

    def validate_external_location(self, location_name: str) -> bool:
        """
        Validate that an external location is accessible.

        Returns:
            bool: True if the location URL is accessible with its credential
        """
        try:
            self._sql(f"VALIDATE EXTERNAL LOCATION `{location_name}`")
            logger.info("External location validated: %s", location_name)
            return True
        except Exception as exc:
            logger.error(
                "External location validation failed: %s | %s", location_name, exc
            )
            return False

    def list_external_locations(self) -> Any:
        """List all external locations visible to current user."""
        return self._sql("SHOW EXTERNAL LOCATIONS")

    def grant_external_location_access(
        self,
        location_name: str,
        principal: str,
        privilege: str = "READ FILES",
    ) -> None:
        """
        Grant privileges on an external location to a principal.

        Args:
            location_name: External location name
            principal:     User email, group name, or 'account users'
            privilege:     'READ FILES', 'WRITE FILES', or 'CREATE EXTERNAL TABLE'

        SQL Generated:
            GRANT READ FILES ON EXTERNAL LOCATION `bronze-location` TO `data-engineers`;
        """
        sql = (
            f"GRANT {privilege} ON EXTERNAL LOCATION `{location_name}` "
            f"TO `{principal}`"
        )
        logger.info(
            "Granting %s on external location %s to %s",
            privilege, location_name, principal,
        )
        self._sql(sql)

    # ------------------------------------------------------------------
    # Catalog Management
    # ------------------------------------------------------------------

    def create_catalog(
        self, config: CatalogConfig, if_not_exists: bool = True
    ) -> None:
        """
        Create a Unity Catalog catalog.

        A catalog is the top-level namespace (catalog.schema.table).
        Managed tables in this catalog will be stored in storage_location.

        Args:
            config:          CatalogConfig
            if_not_exists:   Skip if catalog already exists

        SQL Generated:
            CREATE CATALOG IF NOT EXISTS analytics_prod
            MANAGED LOCATION 'abfss://gold@mydatalake.dfs.core.windows.net/managed/'
            COMMENT 'Production analytics catalog';
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        managed_loc = (
            f"MANAGED LOCATION '{config.storage_location}'"
            if config.storage_location
            else ""
        )

        sql = f"""
            CREATE CATALOG {exists_clause} `{config.catalog_name}`
            {managed_loc}
            COMMENT '{config.comment}'
        """
        logger.info("Creating catalog: %s", config.catalog_name)
        self._sql(sql.strip())

        # Set catalog properties
        for prop_key, prop_value in config.properties.items():
            self._sql(
                f"ALTER CATALOG `{config.catalog_name}` "
                f"SET DBPROPERTIES ('{prop_key}' = '{prop_value}')"
            )
        logger.info("Catalog created: %s", config.catalog_name)

    def create_schema(
        self,
        catalog: str,
        schema: str,
        storage_location: Optional[str] = None,
        comment: str = "",
        if_not_exists: bool = True,
    ) -> None:
        """
        Create a schema within a Unity Catalog catalog.

        Args:
            catalog:           Catalog name
            schema:            Schema (database) name
            storage_location:  External location URL for managed tables in this schema
            comment:           Schema description
            if_not_exists:     Skip if already exists

        SQL Generated:
            CREATE SCHEMA IF NOT EXISTS analytics_prod.sales
            MANAGED LOCATION 'abfss://gold@mydatalake.dfs.core.windows.net/sales/'
            COMMENT 'Sales domain schema';
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        managed_loc = (
            f"MANAGED LOCATION '{storage_location}'" if storage_location else ""
        )

        sql = f"""
            CREATE SCHEMA {exists_clause} `{catalog}`.`{schema}`
            {managed_loc}
            COMMENT '{comment}'
        """
        logger.info("Creating schema: %s.%s", catalog, schema)
        self._sql(sql.strip())

    def create_external_table(
        self,
        catalog: str,
        schema: str,
        table: str,
        location: str,
        format: str = "delta",
        comment: str = "",
        partition_cols: Optional[List[str]] = None,
        if_not_exists: bool = True,
    ) -> None:
        """
        Register an external table in Unity Catalog.

        External tables point to data in an external location.
        Dropping the table only removes metadata — data is preserved in ADLS.

        Args:
            catalog:         Catalog name
            schema:          Schema name
            table:           Table name
            location:        Full abfss:// path to the table data
            format:          Data format: 'delta', 'parquet', 'csv', 'json'
            comment:         Table description
            partition_cols:  Partition columns for non-Delta formats
            if_not_exists:   Skip if table already exists

        SQL Generated:
            CREATE TABLE IF NOT EXISTS analytics_prod.sales.transactions
            USING DELTA
            LOCATION 'abfss://gold@mydatalake.dfs.core.windows.net/sales/transactions/'
            COMMENT 'Sales transaction fact table';
        """
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        partition_clause = (
            f"PARTITIONED BY ({', '.join(partition_cols)})"
            if partition_cols
            else ""
        )

        sql = f"""
            CREATE TABLE {exists_clause} `{catalog}`.`{schema}`.`{table}`
            USING {format.upper()}
            LOCATION '{location}'
            {partition_clause}
            COMMENT '{comment}'
        """
        logger.info(
            "Creating external table: %s.%s.%s at %s",
            catalog, schema, table, location,
        )
        self._sql(sql.strip())

    def create_managed_table_as_select(
        self,
        catalog: str,
        schema: str,
        table: str,
        select_query: str,
        comment: str = "",
        partition_cols: Optional[List[str]] = None,
    ) -> None:
        """
        Create a managed table using CTAS (CREATE TABLE AS SELECT).

        Managed tables are fully owned by Unity Catalog.
        Data is stored in the catalog/schema storage location.
        DROP TABLE will delete the underlying data.

        Args:
            catalog:        Catalog name
            schema:         Schema name
            table:          Table name
            select_query:   SQL SELECT query for table creation
            comment:        Table description
            partition_cols: Partition columns

        SQL Generated:
            CREATE OR REPLACE TABLE analytics_prod.sales.daily_summary
            COMMENT 'Pre-aggregated daily sales summary'
            AS SELECT date, SUM(revenue) ... FROM ...;
        """
        partition_clause = (
            f"PARTITIONED BY ({', '.join(partition_cols)})"
            if partition_cols
            else ""
        )

        sql = f"""
            CREATE OR REPLACE TABLE `{catalog}`.`{schema}`.`{table}`
            {partition_clause}
            COMMENT '{comment}'
            AS {select_query}
        """
        logger.info(
            "Creating managed table (CTAS): %s.%s.%s",
            catalog, schema, table,
        )
        self._sql(sql.strip())

    # ------------------------------------------------------------------
    # Access Control (RBAC)
    # ------------------------------------------------------------------

    def setup_rbac(
        self,
        catalog: str,
        schema: str,
        table: Optional[str],
        principal: str,
        privileges: List[str],
    ) -> None:
        """
        Grant privileges on Unity Catalog objects to a principal.

        Common privilege sets:
            - Data Analyst:     ['SELECT'] on schema/table
            - Data Engineer:    ['SELECT', 'MODIFY', 'CREATE TABLE'] on schema
            - Data Steward:     ['ALL PRIVILEGES'] on catalog
            - Pipeline Service: ['SELECT', 'MODIFY'] on specific tables

        Args:
            catalog:     Catalog name
            schema:      Schema name
            table:       Table name (None for schema-level grants)
            principal:   User, group, or service principal name
            privileges:  List of privilege strings

        SQL Generated (table-level):
            GRANT SELECT, MODIFY ON TABLE analytics_prod.sales.transactions
            TO `data-engineering-team`;
        """
        priv_str = ", ".join(privileges)

        if table:
            object_type = "TABLE"
            object_name = f"`{catalog}`.`{schema}`.`{table}`"
        else:
            object_type = "SCHEMA"
            object_name = f"`{catalog}`.`{schema}`"

        sql = f"GRANT {priv_str} ON {object_type} {object_name} TO `{principal}`"
        logger.info(
            "Granting [%s] on %s %s to %s",
            priv_str, object_type, object_name, principal,
        )
        self._sql(sql)

    def audit_table_permissions(self, catalog: str, schema: str, table: str) -> Any:
        """
        Show all grants on a specific table.

        Returns:
            DataFrame with columns: ActionType, ObjectType, ObjectKey, Principal, Privilege

        SQL Generated:
            SHOW GRANTS ON TABLE analytics_prod.sales.transactions;
        """
        sql = f"SHOW GRANTS ON TABLE `{catalog}`.`{schema}`.`{table}`"
        logger.info("Auditing permissions: %s.%s.%s", catalog, schema, table)
        return self._sql(sql)

    # ------------------------------------------------------------------
    # Metastore Operations
    # ------------------------------------------------------------------

    def get_metastore_info(self) -> Any:
        """Return current metastore information."""
        return self._sql("SELECT * FROM system.information_schema.schemata LIMIT 1")

    def setup_complete_azure_data_lakehouse(
        self,
        storage_account: str,
        access_connector_id: str,
        environment: str = "prod",
    ) -> None:
        """
        Complete Unity Catalog setup for an Azure data lakehouse.

        Creates the full hierarchy:
            Storage Credential → External Locations (bronze/silver/gold)
            → Catalogs → Schemas

        Args:
            storage_account:     ADLS Gen2 storage account name
            access_connector_id: ARM resource ID of Access Connector
            environment:         Deployment environment suffix (prod/dev/staging)

        Steps Performed:
            1. Create storage credential using Access Connector MI
            2. Create external locations for each data zone
            3. Create environment-specific catalogs
            4. Create standard domain schemas
        """
        logger.info(
            "Setting up complete Azure data lakehouse in Unity Catalog "
            "(account=%s, env=%s)",
            storage_account, environment,
        )

        # Step 1: Storage Credential
        cred = StorageCredentialConfig(
            credential_name=f"adls-{environment}-mi-credential",
            credential_type="managed_identity",
            access_connector_id=access_connector_id,
            comment=f"Managed Identity credential for {environment} ADLS Gen2",
        )
        self.create_storage_credential(cred)

        # Step 2: External Locations per zone
        for zone in ("bronze", "silver", "gold"):
            loc = ExternalLocationConfig(
                location_name=f"{zone}-{environment}-location",
                url=(
                    f"abfss://{zone}"
                    f"@{storage_account}.dfs.core.windows.net/"
                ),
                credential_name=cred.credential_name,
                comment=f"{zone.capitalize()} zone external location ({environment})",
            )
            self.create_external_location(loc)

        # Step 3: Catalogs
        for domain in ("raw", "analytics", "serving"):
            cat = CatalogConfig(
                catalog_name=f"{domain}_{environment}",
                storage_location=(
                    f"abfss://gold@{storage_account}.dfs.core.windows.net"
                    f"/managed/{domain}/"
                ),
                comment=f"{domain.capitalize()} catalog for {environment}",
            )
            self.create_catalog(cat)

        # Step 4: Standard schemas
        domains = ["sales", "marketing", "finance", "operations"]
        for domain in domains:
            self.create_schema(
                catalog=f"analytics_{environment}",
                schema=domain,
                storage_location=(
                    f"abfss://gold@{storage_account}.dfs.core.windows.net"
                    f"/managed/analytics/{domain}/"
                ),
                comment=f"{domain.capitalize()} domain schema",
            )

        logger.info(
            "Azure data lakehouse Unity Catalog setup complete for env=%s", environment
        )
