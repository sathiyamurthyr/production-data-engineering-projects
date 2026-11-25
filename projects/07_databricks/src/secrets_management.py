"""
Module 10: Secrets Management — Databricks Secret Scopes & Credential Governance
=================================================================================

Explanation:
    Databricks Secret Scopes provide a secure store for credentials, API tokens, database passwords,
    and storage keys. Scopes can be Databricks-backed (encrypted in control plane database) or
    integrated with external cloud key management services (Azure Key Vault, AWS Secrets Manager).

Business Use Case:
    - Eliminating hardcoded passwords, AWS access keys, or JDBC credentials from Git repositories.
    - Centralizing credential rotation: applications retrieve live secrets dynamically via `dbutils.secrets.get()`.
    - Enforcing granular Access Control Lists (ACLs) so only specific user groups or service principals can read secrets.
    - Zero-log exposure: Databricks automatically redacts secrets retrieved via `dbutils.secrets` from notebook outputs and logs.

Architecture:
    Databricks Notebook / Job Task
                  |
        `dbutils.secrets.get(scope, key)`
                  |
    +-----------------------------------------------+
    |            Secret Scope Management            |
    |  +---------------------+  +-----------------+ |
    |  | Databricks-Backed   |  | Azure Key Vault | |
    |  | Scope (Encrypted)   |  | / AWS KMS Scope | |
    |  +---------------------+  +-----------------+ |
    +-----------------------------------------------+
                  |
         Redacted Secret Return ([REDACTED] in prints)

Performance Notes:
    - Secret scope lookups are cached locally on cluster worker nodes for execution efficiency.
    - Azure Key Vault backed secret scopes validate authorization via Azure AD tenant credentials.

Common Mistakes:
    - Printing secret values using string slicing or format tricks to bypass the `[REDACTED]` printer filter.
    - Storing production secrets in notebook source code files committed to Git repositories.
    - Not assigning READ ACLs on secret scopes to the service principal executing automated jobs.

Interview Questions:
    Q: What are the two types of secret scopes in Databricks and how do they differ?
    A: 1. Databricks-backed scope: Managed entirely within the Databricks workspace control plane.
       2. Azure Key Vault-backed scope: References an Azure Key Vault resource directly; secret updates in AKV reflect instantly in Databricks.

    Q: What happens when you print a variable retrieved via `dbutils.secrets.get()` in a Databricks notebook?
    A: Databricks intercepts the stdout buffer and replaces the exact secret string value with `[REDACTED]`.
"""

import logging
import os
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Production wrapper for securely retrieving credentials across local environments,
    environment variables, and Databricks Secret Scopes.
    """

    def __init__(self, default_scope: str = "prod_data_eng"):
        self.default_scope = default_scope

    def get_secret(self, key: str, scope: Optional[str] = None) -> str:
        """
        Safely resolves a secret value. Priority order:
        1. `dbutils.secrets.get(scope, key)` if running in Databricks runtime.
        2. Environment variable (uppercase: SCOPE_KEY or KEY).
        3. Local fallback dummy value for testing.
        """
        target_scope = scope or self.default_scope

        # Attempt DBUtils retrieval
        try:
            # Check if dbutils is available in runtime
            import IPython
            dbutils = IPython.get_ipython().user_ns.get("dbutils")
            if dbutils and hasattr(dbutils, "secrets"):
                logger.info(f"Retrieving secret '{key}' from Databricks scope '{target_scope}' via dbutils...")
                return dbutils.secrets.get(scope=target_scope, key=key)
        except Exception:
            pass

        # Fallback to Environment Variables
        env_var_name = f"{target_scope.upper()}_{key.upper()}"
        if env_var_name in os.environ:
            logger.info(f"Retrieved secret '{key}' from env var '{env_var_name}'")
            return os.environ[env_var_name]

        if key.upper() in os.environ:
            logger.info(f"Retrieved secret '{key}' from env var '{key.upper()}'")
            return os.environ[key.upper()]

        logger.warning(f"Secret '{key}' not found in DBUtils or Env. Returning mock sanitized token.")
        return f"mock_secret_value_{key}"

    def build_create_scope_cli_command(self, scope_name: str, key_vault_dns: Optional[str] = None, resource_id: Optional[str] = None) -> str:
        """
        Generates Databricks CLI v2 command to create a secret scope.
        """
        if key_vault_dns and resource_id:
            cmd = (
                f"databricks secrets create-scope {scope_name} "
                f"--scope-backend-type AZURE_KEYVAULT "
                f"--dns-name '{key_vault_dns}' "
                f"--resource-id '{resource_id}'"
            )
        else:
            cmd = f"databricks secrets create-scope {scope_name}"
        return cmd

    def build_put_secret_cli_command(self, scope_name: str, key: str, value: str) -> str:
        """
        Generates CLI command to write a secret to a Databricks-backed scope.
        """
        return f"databricks secrets put-secret --scope {scope_name} --key {key} --string-value '{value}'"

    def build_grant_acl_cli_command(self, scope_name: str, principal: str, permission: str = "READ") -> str:
        """
        Generates CLI command to grant ACL permissions on a secret scope.
        """
        return f"databricks secrets put-acl {scope_name} {principal} {permission}"


if __name__ == "__main__":
    sm = SecretsManager(default_scope="prod_finance_scope")

    print("=== Resolved Secret ===")
    db_pass = sm.get_secret("db_password")
    print(f"Password retrieved: {db_pass[:3]}***")

    print("\n=== Databricks CLI Management Commands ===")
    print("Create Scope:", sm.build_create_scope_cli_command("finance_vault"))
    print("Put Secret:", sm.build_put_secret_cli_command("finance_vault", "jdbc_url", "jdbc:postgresql://db.prod:5432/finance"))
    print("Grant ACL:", sm.build_grant_acl_cli_command("finance_vault", "finance_analysts", "READ"))
