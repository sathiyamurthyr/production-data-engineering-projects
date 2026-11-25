"""
Module 04: Unity Catalog — Enterprise Governance, Lineage, and Access Control
=============================================================================

Explanation:
    Unity Catalog (UC) is Databricks' unified governance solution for data and AI assets
    across cloud platforms. It provides centralized access control, auditing, data lineage,
    data discovery, and securable object management using standard SQL and REST APIs.
    The 3-tier namespace structure is: catalog.schema.table (or view, volume, function).

Business Use Case:
    - Enforcing fine-grained Role-Based Access Control (RBAC) across multi-tenant data platforms.
    - Implementing data lineage tracking to trace data from raw landing to BI reports for compliance (GDPR/HIPAA).
    - Attribute-Based Access Control (ABAC) with Dynamic Column Masking and Row-Level Filtering.
    - Centralizing metadata search and data cataloging across AWS, Azure, and GCP workspace deployments.

Architecture:
    +------------------------------------------------------------------+
    |                         Unity Catalog                            |
    |  +------------------------------------------------------------+  |
    |  | Catalog (e.g. prod_finance)                                |  |
    |  |   +------------------------------------------------------+ |  |
    |  |   | Schema / Database (e.g. gold_reporting)             | |  |
    |  |   |   +------------------------------------------------+ | |  |
    |  |   |   | Tables / Views / Volumes / ML Models           | | |  |
    |  |   |   +------------------------------------------------+ | |  |
    |  |   +------------------------------------------------------+ |  |
    |  +------------------------------------------------------------+  |
    +------------------------------------------------------------------+
               |                       |                      |
     Storage Credential       External Location       Access Control Policy

Production Example:
    A global bank uses Unity Catalog to isolate PII data in `prod_pii.vault` with access restricted
    to compliance officers, while exposing masked views to data analysts via dynamic column masks.

Performance Notes:
    - Unity Catalog centralizes metastore access, eliminating metastore synchronization bottlenecks.
    - Privilege checks are cached locally at the compute node level for minimal execution latency.
    - Direct access to underlying cloud storage (S3/ADLS) is governed via short-lived credentials.

Common Mistakes:
    - Using Hive Metastore legacy paths (`hive_metastore.db.table`) instead of UC 3-tier names.
    - Granting direct `ALL PRIVILEGES` to user groups instead of least-privilege role bindings.
    - Hardcoding storage paths instead of binding managed external locations via Unity Catalog.

Interview Questions:
    Q: What is the 3-tier namespace in Unity Catalog and why is it preferred over Hive Metastore?
    A: The 3-tier namespace is `catalog.schema.table`. It allows organizing data across environments
       (e.g., dev, staging, prod) within a single metastore and enables workspace-independent governance.

    Q: How does Row-Level Filtering work in Unity Catalog?
    A: SQL functions defined with `CREATE FUNCTION` can be bound to tables using `ALTER TABLE ... SET ROW FILTER`.
       The function runs implicitly during query execution to evaluate if the current user/group has rights to see a row.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class UnityCatalogObject:
    catalog_name: str
    schema_name: str
    object_name: str
    object_type: str  # TABLE, VIEW, VOLUME, FUNCTION

    @property
    def full_name(self) -> str:
        return f"{self.catalog_name}.{self.schema_name}.{self.object_name}"


class UnityCatalogManager:
    """
    Production-grade wrapper for Unity Catalog metadata operations, governance,
    privilege grants, dynamic data masking, and lineage query helper.
    """

    def __init__(self, spark_session: Optional[Any] = None):
        """
        Initialize Unity Catalog Manager.

        :param spark_session: Optional active PySpark PySpark / Databricks session instance.
        """
        self.spark = spark_session

    def create_catalog(self, catalog_name: str, comment: str = "", properties: Optional[Dict[str, str]] = None) -> str:
        """
        Generates and executes SQL to create a new catalog in Unity Catalog.
        """
        prop_str = ""
        if properties:
            formatted_props = ", ".join([f"'{k}'='{v}'" for k, v in properties.items()])
            prop_str = f" PROPERTIES ({formatted_props})"

        comment_str = f" COMMENT '{comment}'" if comment else ""
        sql = f"CREATE CATALOG IF NOT EXISTS `{catalog_name}`{comment_str}{prop_str};"
        logger.info(f"Executing DDL: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def create_schema(
        self,
        catalog_name: str,
        schema_name: str,
        comment: str = "",
        managed_location: Optional[str] = None,
    ) -> str:
        """
        Creates a schema within a catalog, optionally binding a managed cloud storage location.
        """
        location_str = f" MANAGED LOCATION '{managed_location}'" if managed_location else ""
        comment_str = f" COMMENT '{comment}'" if comment else ""
        sql = f"CREATE SCHEMA IF NOT EXISTS `{catalog_name}`.`{schema_name}`{comment_str}{location_str};"
        logger.info(f"Executing DDL: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def grant_privilege(
        self,
        principal: str,
        privilege: str,
        securable_type: str,
        securable_name: str,
    ) -> str:
        """
        Grants specified privilege to a user or group on a securable object.

        :param principal: User, group, or service principal name (e.g. `data_analysts`).
        :param privilege: Privilege type (e.g., `SELECT`, `MODIFY`, `USE CATALOG`, `CREATE TABLE`).
        :param securable_type: Object type (CATALOG, SCHEMA, TABLE, VOLUME, EXTERNAL LOCATION).
        :param securable_name: Full 3-tier object identifier.
        """
        sql = f"GRANT {privilege} ON {securable_type} {securable_name} TO `{principal}`;"
        logger.info(f"Granting privilege: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def revoke_privilege(
        self,
        principal: str,
        privilege: str,
        securable_type: str,
        securable_name: str,
    ) -> str:
        """
        Revokes a privilege from a principal.
        """
        sql = f"REVOKE {privilege} ON {securable_type} {securable_name} FROM `{principal}`;"
        logger.info(f"Revoking privilege: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def apply_column_mask(
        self,
        catalog_name: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        mask_function_name: str,
    ) -> str:
        """
        Applies a dynamic data masking function to a column in a Unity Catalog table.
        """
        full_table = f"`{catalog_name}`.`{schema_name}`.`{table_name}`"
        sql = f"ALTER TABLE {full_table} ALTER COLUMN `{column_name}` SET MASK {mask_function_name};"
        logger.info(f"Applying column mask: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def apply_row_filter(
        self,
        catalog_name: str,
        schema_name: str,
        table_name: str,
        filter_function_name: str,
        filter_column: str,
    ) -> str:
        """
        Binds a row filter function to a table to enforce row-level security.
        """
        full_table = f"`{catalog_name}`.`{schema_name}`.`{table_name}`"
        sql = f"ALTER TABLE {full_table} SET ROW FILTER {filter_function_name} ON (`{filter_column}`);"
        logger.info(f"Applying row filter: {sql}")

        if self.spark:
            self.spark.sql(sql)
        return sql

    def generate_mask_udf_sql(self, schema_name: str, function_name: str) -> str:
        """
        Generates SQL to create a standard PII masking UDF checking group membership.
        """
        sql = f"""
CREATE OR REPLACE FUNCTION `{schema_name}`.`{function_name}`(val STRING)
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('pii_admins') THEN val
  WHEN val IS NULL THEN NULL
  ELSE CONCAT('XXX-XX-', RIGHT(val, 4))
END;
        """.strip()
        return sql

    def list_table_lineage_sql(self, full_table_name: str) -> str:
        """
        Generates system table query for lineage discovery in Unity Catalog.
        """
        sql = f"""
SELECT
    source_table_full_name,
    target_table_full_name,
    event_time,
    entity_type
FROM system.access.table_lineage
WHERE target_table_full_name = '{full_table_name}'
   OR source_table_full_name = '{full_table_name}'
ORDER BY event_time DESC
LIMIT 100;
        """.strip()
        return sql


if __name__ == "__main__":
    uc_mgr = UnityCatalogManager()
    print("=== Demo Unity Catalog DDL Generation ===")
    print(uc_mgr.create_catalog("prod_finance", comment="Production Financial Data"))
    print(uc_mgr.create_schema("prod_finance", "gold_reporting", comment="Gold Tier Aggregates"))
    print(uc_mgr.grant_privilege("data_analysts", "SELECT", "TABLE", "`prod_finance`.`gold_reporting`.`quarterly_rev`"))
    print(uc_mgr.generate_mask_udf_sql("gold_reporting", "mask_ssn"))
    print(uc_mgr.list_table_lineage_sql("prod_finance.gold_reporting.quarterly_rev"))
