"""
Module 01: Databricks Connect — Remote Cluster Connection & Authentication Patterns
===================================================================================

Explanation:
    Databricks Connect (v2) lets you run Apache Spark code on a remote Databricks
    cluster from your local IDE or CI environment. It replaces the need to upload
    notebooks: your local Python files execute ON the cluster but feel local.

Business Use Case:
    - Local IDE development with full Spark power (no need for costly persistent clusters)
    - Unit testing Spark transformations before deploying to production jobs
    - Running Databricks notebooks from CI/CD pipelines without workspace overhead
    - Interactive debugging of distributed code from VSCode / PyCharm

Architecture:
    Local Code (Python)
        → Databricks Connect Client (gRPC)
            → Databricks Control Plane (auth, routing)
                → Customer Data Plane (Spark Cluster)
                    → Delta Lake / Cloud Storage

Authentication Modes:
    1. Personal Access Token (PAT)          — development / testing
    2. OAuth Machine-to-Machine (M2M)       — production / CI/CD
    3. Azure Managed Identity               — Azure-native production
    4. AWS IAM Role                         — AWS-native production

Requirements:
    pip install databricks-connect==14.3.*

Performance Notes:
    - Databricks Connect uses gRPC for efficient binary serialization
    - The cluster MUST be running before connecting (cold start overhead)
    - Use cluster pools to reduce cold start time from ~5min to ~30s
    - Databricks Connect v2 supports serverless compute (no cluster required)

Common Mistakes:
    - Mismatching databricks-connect version with cluster Spark version
    - Using DBR < 13.x (only DBR 13+ supports Connect v2)
    - Forgetting to set SPARK_REMOTE env var for gRPC tunnel
    - Hardcoding PAT tokens in source code (use env vars or secret managers)

Interview Questions:
    Q: What is Databricks Connect v2 and how does it differ from v1?
    A: v2 uses gRPC + Apache Arrow for efficient data transfer, supports DBR 13+,
       and integrates with the Databricks SDK. v1 used Py4J locally which was brittle.

    Q: When would you NOT use Databricks Connect?
    A: For production batch jobs (use Databricks Jobs instead), very large local
       data transfers, or when cluster boot time is unacceptable for the use case.

    Q: How does OAuth M2M authentication work in Databricks?
    A: Register a Service Principal in Azure AD / AWS IAM, generate client credentials,
       and exchange them for short-lived OAuth tokens. The SDK handles token refresh.

Author: Sathiya Murthy
Blog: Data Engineering Diaries
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ── conditional imports so the module is importable without installing the full SDK ──
try:
    from databricks.connect import DatabricksSession
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.config import Config
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    DatabricksSession = None   # type: ignore[misc,assignment]
    WorkspaceClient = None     # type: ignore[misc,assignment]
    Config = None              # type: ignore[misc,assignment]

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes & Enums
# ─────────────────────────────────────────────────────────────────────────────

class AuthMethod(str, Enum):
    """Supported Databricks authentication methods."""
    PAT = "pat"                    # Personal Access Token
    OAUTH_M2M = "oauth_m2m"       # Machine-to-Machine OAuth (Service Principal)
    AZURE_MSI = "azure_msi"       # Azure Managed Service Identity
    AWS_IAM = "aws_iam"           # AWS IAM Role (Instance Profile)
    PROFILE = "profile"           # Databricks CLI profile (~/.databrickscfg)


@dataclass
class DatabricksConnectionConfig:
    """
    Immutable connection configuration for a Databricks workspace.

    Never store tokens in source code. Use environment variables or
    a secret manager (Azure Key Vault, AWS Secrets Manager, Databricks Secrets).
    """
    host: str                                           # e.g. https://adb-1234.azuredatabricks.net
    auth_method: AuthMethod = AuthMethod.PAT
    token: Optional[str] = None                        # PAT — loaded from env var
    client_id: Optional[str] = None                    # OAuth M2M client ID
    client_secret: Optional[str] = None               # OAuth M2M secret — env var only
    cluster_id: Optional[str] = None                  # Target compute cluster
    profile: Optional[str] = None                     # CLI profile name
    http_path: Optional[str] = None                   # SQL Warehouse HTTP path
    timeout_seconds: int = 30
    tags: dict = field(default_factory=dict)

    @classmethod
    def from_environment(cls) -> "DatabricksConnectionConfig":
        """
        Load configuration from environment variables.

        Environment variables used:
            DATABRICKS_HOST         — workspace URL
            DATABRICKS_TOKEN        — PAT (Personal Access Token)
            DATABRICKS_CLUSTER_ID   — target cluster
            DATABRICKS_HTTP_PATH    — SQL Warehouse HTTP path
            DATABRICKS_CLIENT_ID    — OAuth M2M client ID
            DATABRICKS_CLIENT_SECRET— OAuth M2M secret
        """
        host = os.environ.get("DATABRICKS_HOST", "")
        if not host:
            raise EnvironmentError(
                "DATABRICKS_HOST environment variable is not set. "
                "Set it to your workspace URL, e.g.: "
                "https://adb-<workspace-id>.azuredatabricks.net"
            )

        token = os.environ.get("DATABRICKS_TOKEN")
        client_id = os.environ.get("DATABRICKS_CLIENT_ID")
        client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")

        # Determine auth method from available credentials
        if client_id and client_secret:
            auth_method = AuthMethod.OAUTH_M2M
        elif token:
            auth_method = AuthMethod.PAT
        else:
            auth_method = AuthMethod.PROFILE  # Fall back to CLI profile

        return cls(
            host=host,
            auth_method=auth_method,
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            cluster_id=os.environ.get("DATABRICKS_CLUSTER_ID"),
            http_path=os.environ.get("DATABRICKS_HTTP_PATH"),
        )

    @classmethod
    def from_cli_profile(cls, profile: str = "DEFAULT") -> "DatabricksConnectionConfig":
        """
        Load configuration from ~/.databrickscfg CLI profile.

        Run 'databricks configure --profile <name>' to set up a profile.
        """
        return cls(
            host="",          # SDK reads from profile automatically
            auth_method=AuthMethod.PROFILE,
            profile=profile,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DatabricksConnector
# ─────────────────────────────────────────────────────────────────────────────

class DatabricksConnector:
    """
    Production-grade Databricks connector that supports multiple auth methods.

    Usage:
        # PAT via environment variable
        connector = DatabricksConnector.from_env()
        spark = connector.get_spark()
        df = spark.read.table("catalog.schema.table")
        df.show()

        # OAuth M2M for CI/CD
        config = DatabricksConnectionConfig(
            host="https://adb-1234.azuredatabricks.net",
            auth_method=AuthMethod.OAUTH_M2M,
            client_id="<service-principal-id>",
            client_secret=os.environ["SP_SECRET"],
        )
        connector = DatabricksConnector(config)
    """

    def __init__(self, config: DatabricksConnectionConfig) -> None:
        if not HAS_SDK:
            raise ImportError(
                "databricks-connect is not installed. "
                "Install it with: pip install databricks-connect==14.3.*"
            )
        self._config = config
        self._spark = None
        self._workspace_client = None
        log.info("DatabricksConnector initialized | host=%s | auth=%s",
                 config.host, config.auth_method.value)

    @classmethod
    def from_env(cls) -> "DatabricksConnector":
        """Convenience factory — loads config from environment variables."""
        config = DatabricksConnectionConfig.from_environment()
        return cls(config)

    @classmethod
    def from_profile(cls, profile: str = "DEFAULT") -> "DatabricksConnector":
        """Convenience factory — loads config from Databricks CLI profile."""
        config = DatabricksConnectionConfig.from_cli_profile(profile)
        return cls(config)

    def _build_sdk_config(self) -> "Config":
        """Build a Databricks SDK Config from our connection config."""
        cfg = self._config
        kwargs: dict = {"host": cfg.host}

        if cfg.auth_method == AuthMethod.PAT:
            kwargs["token"] = cfg.token
        elif cfg.auth_method == AuthMethod.OAUTH_M2M:
            kwargs["client_id"] = cfg.client_id
            kwargs["client_secret"] = cfg.client_secret
        elif cfg.auth_method == AuthMethod.PROFILE:
            kwargs = {"profile": cfg.profile}

        return Config(**kwargs)

    def get_spark(self):
        """
        Return a remote SparkSession connected to the Databricks cluster.

        The first call establishes the gRPC connection. Subsequent calls
        return the cached session (singleton pattern per process).

        Returns:
            SparkSession: A SparkSession backed by the remote Databricks cluster.

        Raises:
            RuntimeError: If cluster_id is not configured for cluster-based connect.
        """
        if self._spark is not None:
            return self._spark

        cfg = self._config

        if cfg.cluster_id:
            # Classic cluster-based Databricks Connect
            log.info("Connecting to cluster: %s", cfg.cluster_id)
            builder = (
                DatabricksSession.builder
                .remote(
                    host=cfg.host,
                    token=cfg.token,
                    cluster_id=cfg.cluster_id,
                )
            )
        else:
            # Serverless compute (DBR 14+, no cluster needed)
            log.info("Connecting via serverless compute")
            sdk_config = self._build_sdk_config()
            builder = DatabricksSession.builder.sdkConfig(sdk_config)

        self._spark = builder.getOrCreate()
        log.info("SparkSession established | version=%s", self._spark.version)
        return self._spark

    def get_workspace_client(self) -> "WorkspaceClient":
        """
        Return a Databricks SDK WorkspaceClient for REST API operations.

        The WorkspaceClient provides strongly-typed access to all Databricks APIs:
        clusters, jobs, notebooks, secrets, SQL warehouses, Unity Catalog, etc.

        Returns:
            WorkspaceClient: Authenticated SDK client.
        """
        if self._workspace_client is not None:
            return self._workspace_client

        sdk_config = self._build_sdk_config()
        self._workspace_client = WorkspaceClient(config=sdk_config)
        log.info("WorkspaceClient initialized for host: %s", self._config.host)
        return self._workspace_client

    def test_connectivity(self) -> dict:
        """
        Validate connectivity to the Databricks workspace.

        Returns a dict with connection health information useful for
        health-check endpoints and CI/CD pre-flight checks.

        Returns:
            dict: {
                "status": "ok" | "error",
                "workspace_url": str,
                "current_user": str,
                "spark_version": str | None,
            }
        """
        result: dict = {
            "status": "error",
            "workspace_url": self._config.host,
            "current_user": None,
            "spark_version": None,
        }

        try:
            wc = self.get_workspace_client()
            me = wc.current_user.me()
            result["current_user"] = me.user_name
            result["status"] = "ok"
            log.info("Connectivity test passed | user=%s", me.user_name)
        except Exception as exc:
            log.error("Connectivity test failed: %s", exc)
            result["error"] = str(exc)

        return result

    def verify_spark(self) -> bool:
        """
        Verify SparkSession is live by running a trivial remote computation.

        Returns:
            bool: True if Spark is reachable and responsive.
        """
        try:
            spark = self.get_spark()
            count = spark.range(10).count()
            log.info("Spark verification passed | range(10).count() = %d", count)
            return count == 10
        except Exception as exc:
            log.error("Spark verification failed: %s", exc)
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Pattern Examples
# ─────────────────────────────────────────────────────────────────────────────

def pat_authentication_example() -> None:
    """
    Example: Personal Access Token (PAT) Authentication.

    PAT is the simplest auth method, suitable for development and testing.
    NEVER commit PAT tokens to source control.

    Generate a PAT:
        Databricks Workspace → User Settings → Developer → Access Tokens → Generate New Token
    """
    # Pattern 1: Explicit PAT configuration
    config = DatabricksConnectionConfig(
        host="https://adb-1234567890123456.7.azuredatabricks.net",
        auth_method=AuthMethod.PAT,
        token=os.environ["DATABRICKS_TOKEN"],  # Always from env var
        cluster_id="0101-123456-abcdefgh",
    )
    connector = DatabricksConnector(config)

    health = connector.test_connectivity()
    print(f"Connected as: {health['current_user']}")


def oauth_m2m_authentication_example() -> None:
    """
    Example: OAuth Machine-to-Machine (M2M) Authentication.

    Recommended for production CI/CD pipelines. Uses Azure Service Principal
    or Databricks Service Principal credentials.

    Setup steps (Azure):
        1. Create Azure App Registration
        2. Add as Databricks admin: Settings → Service Principals → Add
        3. Generate client secret (store in Azure Key Vault)
        4. Set environment variables in your CI system
    """
    config = DatabricksConnectionConfig(
        host=os.environ["DATABRICKS_HOST"],
        auth_method=AuthMethod.OAUTH_M2M,
        client_id=os.environ["DATABRICKS_CLIENT_ID"],
        client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
    )
    connector = DatabricksConnector(config)
    health = connector.test_connectivity()
    print(f"OAuth M2M connected as service principal: {health['current_user']}")


def cli_profile_authentication_example() -> None:
    """
    Example: Databricks CLI Profile Authentication.

    The most ergonomic option for local development. Run once to configure:
        databricks configure --profile my-workspace

    The SDK reads from ~/.databrickscfg automatically.
    """
    connector = DatabricksConnector.from_profile(profile="prod-workspace")
    health = connector.test_connectivity()
    print(f"Profile auth connected: {health['current_user']}")


def serverless_compute_example() -> None:
    """
    Example: Serverless Compute Connection (no cluster needed).

    Databricks Serverless (DBR 14+) provides instant compute without
    cluster startup time. Billed per DBU-second.

    Benefits:
        - Zero startup time (< 1 second connection)
        - No cluster management overhead
        - Automatic scaling
        - Per-second billing (no wasted idle time)
    """
    config = DatabricksConnectionConfig(
        host=os.environ["DATABRICKS_HOST"],
        auth_method=AuthMethod.OAUTH_M2M,
        client_id=os.environ["DATABRICKS_CLIENT_ID"],
        client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
        # No cluster_id — serverless compute is used automatically
    )
    connector = DatabricksConnector(config)
    spark = connector.get_spark()

    # Run Spark operations remotely with no cluster cold start
    result = spark.sql("SELECT current_timestamp() as ts, current_user() as user")
    result.show()


# ─────────────────────────────────────────────────────────────────────────────
# Context Manager Support
# ─────────────────────────────────────────────────────────────────────────────

class ManagedDatabricksSession:
    """
    Context manager for Databricks SparkSession lifecycle management.

    Usage:
        with ManagedDatabricksSession(config) as spark:
            df = spark.read.table("prod.sales.orders")
            df.write.mode("overwrite").saveAsTable("dev.sales.orders_copy")
        # Session is properly closed on exit
    """

    def __init__(self, config: DatabricksConnectionConfig) -> None:
        self._connector = DatabricksConnector(config)
        self._spark = None

    def __enter__(self):
        self._spark = self._connector.get_spark()
        return self._spark

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._spark:
            try:
                self._spark.stop()
                log.info("SparkSession closed cleanly")
            except Exception as e:
                log.warning("Error closing SparkSession: %s", e)
        # Don't suppress exceptions
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Module 01: Databricks Connect")
    print("=" * 60)
    print()
    print("Authentication Methods Available:")
    for method in AuthMethod:
        print(f"  • {method.value}")
    print()
    print("To test connectivity, set environment variables and run:")
    print("  DATABRICKS_HOST=https://... DATABRICKS_TOKEN=dapi... python databricks_connect.py")
    print()

    # Only run connectivity test if env vars are set
    if os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN"):
        connector = DatabricksConnector.from_env()
        result = connector.test_connectivity()
        print(f"Connectivity Result: {result}")
    else:
        print("Set DATABRICKS_HOST and DATABRICKS_TOKEN to test live connectivity.")
