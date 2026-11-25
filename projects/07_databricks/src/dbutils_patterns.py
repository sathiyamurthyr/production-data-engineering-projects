"""
Module 03: dbutils Patterns — Databricks Utilities Usage
=========================================================

Explanation:
    dbutils (Databricks Utilities) is available in every Databricks notebook
    and provides utilities for: file system operations (dbutils.fs),
    secret management (dbutils.secrets), widget parameters (dbutils.widgets),
    notebook orchestration (dbutils.notebook), and library management (dbutils.library).

    dbutils is ONLY available inside Databricks notebooks. For local development,
    use the mock stubs provided in this module.

Business Use Case:
    - Reading/writing files on DBFS or cloud storage without knowing the underlying paths
    - Parameterizing notebooks with widgets (making them reusable for different dates/regions)
    - Retrieving secrets safely (Key Vault or Databricks-backed)
    - Chaining notebooks together in complex workflows

Production Example:
    A daily ETL notebook uses dbutils.widgets to accept the processing date,
    reads raw data from ADLS using dbutils.fs.ls, fetches DB credentials
    via dbutils.secrets, and returns a JSON result to the orchestrating notebook.

Performance Notes:
    - dbutils.fs.cp copies files within DBFS without driver memory bottleneck
    - For large-scale file listing, use spark.read.format("binaryFile") instead of dbutils.fs.ls
    - dbutils.notebook.run() is single-threaded per call; use Jobs for parallel execution

Common Mistakes:
    - Calling dbutils outside notebooks (not available in .py files running locally)
    - Logging secret values — NEVER print or log dbutils.secrets.get() results
    - Using dbutils.fs.ls recursively on deep ADLS hierarchies (very slow)
    - Not calling dbutils.widgets.removeAll() at notebook start (stale widget values)

Interview Questions:
    Q: How do dbutils.secrets work and what are the two types of secret scopes?
    A: Secret scopes store key-value secrets. Two types:
       1. Databricks-backed: Stored in Databricks' encrypted store
       2. Azure Key Vault-backed: Backed by AKV (recommended for Azure)
       Access: dbutils.secrets.get(scope="my-scope", key="my-key")

    Q: What is the difference between dbutils.notebook.run() and %run?
    A: %run includes the notebook inline (shares variable scope, no return value).
       dbutils.notebook.run() calls as a subprocess (isolated scope, returns string,
       supports timeout and parameter passing). Use run() for orchestration.

    Q: How would you parameterize a notebook for different environments?
    A: Use dbutils.widgets.text/dropdown to define input parameters.
       In production: values are passed via job task parameters (notebook_params).
       For local testing: set widget defaults that work standalone.

Author: Sathiya Murthy
Blog: Data Engineering Diaries
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


# ─────────────────────────────────────────────────────────────────────────────
# Mock dbutils for local development and testing
# ─────────────────────────────────────────────────────────────────────────────

class MockFileInfo:
    """Mock of the FileInfo object returned by dbutils.fs.ls"""
    def __init__(self, path: str, name: str, size: int, modification_time: int = 0):
        self.path = path
        self.name = name
        self.size = size
        self.modificationTime = modification_time

    def __repr__(self):
        return f"FileInfo(path={self.path!r}, name={self.name!r}, size={self.size})"


class MockFsUtils:
    """
    Mock implementation of dbutils.fs for local testing.
    Operations are no-ops or use the local filesystem.
    """
    def ls(self, path: str) -> List[MockFileInfo]:
        """List files at the given path (returns empty list in mock)."""
        log.info("[MOCK] dbutils.fs.ls('%s')", path)
        return []

    def cp(self, src: str, dst: str, recurse: bool = False) -> bool:
        log.info("[MOCK] dbutils.fs.cp('%s' -> '%s', recurse=%s)", src, dst, recurse)
        return True

    def mv(self, src: str, dst: str, recurse: bool = False) -> bool:
        log.info("[MOCK] dbutils.fs.mv('%s' -> '%s', recurse=%s)", src, dst, recurse)
        return True

    def rm(self, path: str, recurse: bool = False) -> bool:
        log.info("[MOCK] dbutils.fs.rm('%s', recurse=%s)", path, recurse)
        return True

    def mkdirs(self, path: str) -> bool:
        log.info("[MOCK] dbutils.fs.mkdirs('%s')", path)
        return True

    def put(self, path: str, contents: str, overwrite: bool = False) -> bool:
        log.info("[MOCK] dbutils.fs.put('%s', overwrite=%s)", path, overwrite)
        return True

    def head(self, path: str, max_bytes: int = 65536) -> str:
        log.info("[MOCK] dbutils.fs.head('%s', max_bytes=%d)", path, max_bytes)
        return ""

    def mount(self, source: str, mount_point: str, **kwargs) -> bool:
        log.info("[MOCK] dbutils.fs.mount('%s' -> '%s')", source, mount_point)
        return True

    def unmount(self, mount_point: str) -> bool:
        log.info("[MOCK] dbutils.fs.unmount('%s')", mount_point)
        return True

    def mounts(self) -> List[dict]:
        log.info("[MOCK] dbutils.fs.mounts()")
        return []


class MockSecretsUtils:
    """
    Mock implementation of dbutils.secrets for local testing.
    Reads from environment variables with format: DBSECRET_<SCOPE>_<KEY>.
    """
    def get(self, scope: str, key: str) -> str:
        """
        Get a secret value.
        In mock mode, reads from env var: DBSECRET_{SCOPE}_{KEY}
        """
        env_key = f"DBSECRET_{scope.upper()}_{key.upper()}".replace("-", "_")
        value = os.environ.get(env_key, "")
        if not value:
            log.warning(
                "[MOCK] Secret not found: scope=%s, key=%s. "
                "Set env var %s for local testing.",
                scope, key, env_key
            )
        return value

    def list(self, scope: str) -> List[str]:
        """List secret keys in a scope."""
        log.info("[MOCK] dbutils.secrets.list('%s')", scope)
        prefix = f"DBSECRET_{scope.upper()}_"
        return [
            k[len(prefix):].lower()
            for k in os.environ
            if k.startswith(prefix)
        ]

    def listScopes(self) -> List[str]:
        log.info("[MOCK] dbutils.secrets.listScopes()")
        scopes = set()
        for k in os.environ:
            if k.startswith("DBSECRET_"):
                parts = k.split("_")
                if len(parts) >= 3:
                    scopes.add(parts[1].lower())
        return list(scopes)


class MockWidgetsUtils:
    """
    Mock implementation of dbutils.widgets for local testing.
    Widget values can be set via the _overrides dict.
    """
    def __init__(self) -> None:
        self._widgets: Dict[str, str] = {}

    def text(self, name: str, default: str, label: str = "") -> None:
        if name not in self._widgets:
            self._widgets[name] = default
        log.info("[MOCK] Widget text('%s', default='%s')", name, default)

    def dropdown(self, name: str, default: str, choices: List[str], label: str = "") -> None:
        if name not in self._widgets:
            self._widgets[name] = default
        log.info("[MOCK] Widget dropdown('%s', default='%s', choices=%s)", name, default, choices)

    def combobox(self, name: str, default: str, choices: List[str], label: str = "") -> None:
        if name not in self._widgets:
            self._widgets[name] = default

    def multiselect(self, name: str, default: str, choices: List[str], label: str = "") -> None:
        if name not in self._widgets:
            self._widgets[name] = default

    def get(self, name: str) -> str:
        value = self._widgets.get(name, "")
        log.info("[MOCK] Widget get('%s') -> '%s'", name, value)
        return value

    def getAll(self) -> Dict[str, str]:
        return dict(self._widgets)

    def remove(self, name: str) -> None:
        self._widgets.pop(name, None)

    def removeAll(self) -> None:
        self._widgets.clear()
        log.info("[MOCK] All widgets removed")

    def set(self, name: str, value: str) -> None:
        """Test helper: set widget value programmatically."""
        self._widgets[name] = value


class MockNotebookUtils:
    """Mock implementation of dbutils.notebook."""
    def run(
        self,
        path: str,
        timeout_seconds: int,
        arguments: Optional[Dict[str, str]] = None,
    ) -> str:
        log.info(
            "[MOCK] dbutils.notebook.run('%s', timeout=%d, args=%s)",
            path, timeout_seconds, arguments
        )
        return json.dumps({"status": "mock_success", "path": path})

    def exit(self, value: str) -> None:
        log.info("[MOCK] dbutils.notebook.exit('%s')", value)
        raise SystemExit(0)


class MockDbutils:
    """
    Complete mock of Databricks dbutils for local development and testing.

    Usage in tests:
        dbutils = MockDbutils()
        dbutils.widgets.set("env", "staging")
        dbutils.widgets.set("date", "2024-01-15")

        # Now run code that uses dbutils
        result = my_notebook_function(dbutils=dbutils)
    """
    def __init__(self) -> None:
        self.fs = MockFsUtils()
        self.secrets = MockSecretsUtils()
        self.widgets = MockWidgetsUtils()
        self.notebook = MockNotebookUtils()


# ─────────────────────────────────────────────────────────────────────────────
# Production dbutils patterns
# ─────────────────────────────────────────────────────────────────────────────

class NotebookParameters:
    """
    Production pattern for managing notebook widget parameters.

    Encapsulates widget setup and typed value retrieval. This makes notebooks
    testable: inject dbutils mock instead of relying on Databricks runtime.

    Usage (in notebook):
        params = NotebookParameters(dbutils)
        params.setup()
        env = params.environment
        dt = params.processing_date
    """

    def __init__(self, dbutils_ref: Any) -> None:
        """
        Args:
            dbutils_ref: The actual dbutils (in notebooks) or MockDbutils (in tests).
        """
        self._dbutils = dbutils_ref

    def setup(self) -> None:
        """
        Define all widgets for this notebook.

        Call this at the TOP of every notebook that accepts parameters.
        Always call removeAll() first to reset stale widget state.
        """
        # Remove stale widgets from previous runs
        self._dbutils.widgets.removeAll()

        # Environment selector
        self._dbutils.widgets.dropdown(
            name="env",
            default="dev",
            choices=["dev", "staging", "prod"],
            label="Environment",
        )

        # Processing date (ISO format)
        self._dbutils.widgets.text(
            name="processing_date",
            default=date.today().isoformat(),
            label="Processing Date (YYYY-MM-DD)",
        )

        # Source table for parameterized ETL
        self._dbutils.widgets.text(
            name="source_catalog",
            default="dev",
            label="Source Catalog",
        )

        # Dry run mode
        self._dbutils.widgets.dropdown(
            name="dry_run",
            default="true",
            choices=["true", "false"],
            label="Dry Run (no writes)",
        )

    @property
    def environment(self) -> str:
        """Get the target environment."""
        return self._dbutils.widgets.get("env")

    @property
    def processing_date(self) -> date:
        """Get the processing date as a Python date object."""
        raw = self._dbutils.widgets.get("processing_date")
        try:
            return date.fromisoformat(raw)
        except ValueError:
            log.warning("Invalid processing_date '%s', using today", raw)
            return date.today()

    @property
    def source_catalog(self) -> str:
        """Get the source catalog name."""
        return self._dbutils.widgets.get("source_catalog")

    @property
    def is_dry_run(self) -> bool:
        """Whether this is a dry run (no actual writes)."""
        return self._dbutils.widgets.get("dry_run").lower() == "true"

    def as_dict(self) -> Dict[str, Any]:
        """Return all parameters as a dict (for logging)."""
        return {
            "env": self.environment,
            "processing_date": self.processing_date.isoformat(),
            "source_catalog": self.source_catalog,
            "is_dry_run": self.is_dry_run,
        }


class SecureCredentialLoader:
    """
    Production pattern for loading credentials via dbutils.secrets.

    Never hardcode credentials. Never log secret values.
    Use this class to centralize all secret access.
    """

    def __init__(self, dbutils_ref: Any, scope: str) -> None:
        self._dbutils = dbutils_ref
        self._scope = scope
        self._cache: Dict[str, str] = {}

    def get(self, key: str) -> str:
        """
        Retrieve a secret by key from the configured scope.

        Secrets are cached for the lifetime of this object.
        The returned value is NEVER logged.
        """
        if key not in self._cache:
            self._cache[key] = self._dbutils.secrets.get(
                scope=self._scope, key=key
            )
        return self._cache[key]

    def get_jdbc_url(
        self,
        server_key: str = "db-server",
        port_key: str = "db-port",
        database_key: str = "db-name",
        driver: str = "com.microsoft.sqlserver.jdbc.SQLServerDriver",
    ) -> str:
        """Build a JDBC URL from secrets without exposing individual values."""
        server = self.get(server_key)
        port = self.get(port_key)
        database = self.get(database_key)
        return f"jdbc:sqlserver://{server}:{port};database={database}"

    def get_connection_properties(
        self,
        user_key: str = "db-user",
        password_key: str = "db-password",
    ) -> Dict[str, str]:
        """
        Return JDBC connection properties for spark.read.jdbc().

        Returns:
            dict with "user" and "password" keys (values from secrets).
        """
        return {
            "user": self.get(user_key),
            "password": self.get(password_key),
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
        }


class FileSystemHelper:
    """
    Production patterns for working with dbutils.fs.

    Provides common file system operations with proper error handling
    and logging.
    """

    def __init__(self, dbutils_ref: Any) -> None:
        self._fs = dbutils_ref.fs

    def ls_recursive(self, path: str, extension: Optional[str] = None) -> List[str]:
        """
        Recursively list all files under a path.

        Args:
            path: DBFS or cloud storage path.
            extension: Optional file extension filter (e.g., ".parquet").

        Returns:
            List of full file paths.
        """
        result = []
        try:
            items = self._fs.ls(path)
        except Exception as exc:
            log.error("Error listing path %s: %s", path, exc)
            return result

        for item in items:
            if item.name.endswith("/"):
                # Directory — recurse
                result.extend(self.ls_recursive(item.path, extension))
            else:
                if extension is None or item.name.endswith(extension):
                    result.append(item.path)

        return result

    def count_files(self, path: str, extension: Optional[str] = None) -> int:
        """Count files at a path with optional extension filter."""
        return len(self.ls_recursive(path, extension))

    def ensure_path_exists(self, path: str) -> None:
        """Create a directory path if it doesn't exist."""
        self._fs.mkdirs(path)
        log.info("Ensured path exists: %s", path)

    def safe_delete(self, path: str, recurse: bool = False) -> bool:
        """
        Delete a path, returning False instead of raising on error.
        Useful in cleanup code where the path may or may not exist.
        """
        try:
            return self._fs.rm(path, recurse=recurse)
        except Exception as exc:
            log.warning("Failed to delete %s: %s", path, exc)
            return False

    def move_to_archive(self, src_path: str, archive_base: str) -> str:
        """
        Move a file to an archive directory with date partitioning.

        Args:
            src_path: Source file path.
            archive_base: Base archive path (e.g., "abfss://archive@storage.dfs.core.windows.net/").

        Returns:
            The destination path.
        """
        today = datetime.utcnow().strftime("%Y/%m/%d")
        filename = src_path.split("/")[-1]
        dst_path = f"{archive_base.rstrip('/')}/{today}/{filename}"
        self._fs.mv(src_path, dst_path)
        log.info("Archived: %s -> %s", src_path, dst_path)
        return dst_path


def mount_azure_storage(
    dbutils_ref: Any,
    storage_account: str,
    container: str,
    mount_point: str,
    scope: str = "azure-storage",
    key_name: str = "storage-access-key",
) -> None:
    """
    Mount an Azure Blob Storage container to DBFS.

    NOTE: DBFS mounts are deprecated in favor of Unity Catalog external locations.
    Use this pattern only for clusters not attached to Unity Catalog.

    Args:
        dbutils_ref: dbutils reference.
        storage_account: Azure storage account name.
        container: Container name.
        mount_point: DBFS mount point (e.g., /mnt/raw-data).
        scope: Databricks secret scope name.
        key_name: Secret key containing the storage account key.
    """
    # Check if already mounted
    existing_mounts = {m["mountPoint"] for m in dbutils_ref.fs.mounts()}
    if mount_point in existing_mounts:
        log.info("Already mounted: %s", mount_point)
        return

    storage_key = dbutils_ref.secrets.get(scope=scope, key=key_name)
    source = f"wasbs://{container}@{storage_account}.blob.core.windows.net"

    dbutils_ref.fs.mount(
        source=source,
        mount_point=mount_point,
        extra_configs={
            f"fs.azure.account.key.{storage_account}.blob.core.windows.net": storage_key
        }
    )
    log.info("Mounted %s -> %s", source, mount_point)


if __name__ == "__main__":
    print("=" * 60)
    print("Module 03: dbutils Patterns")
    print("=" * 60)

    # Demo with mock dbutils
    dbutils = MockDbutils()

    print("\n--- Widget Parameter Demo ---")
    params = NotebookParameters(dbutils)
    params.setup()
    dbutils.widgets.set("env", "staging")
    dbutils.widgets.set("processing_date", "2024-06-15")

    print(f"Environment:      {params.environment}")
    print(f"Processing Date:  {params.processing_date}")
    print(f"Source Catalog:   {params.source_catalog}")
    print(f"Dry Run:          {params.is_dry_run}")
    print(f"All params:       {params.as_dict()}")

    print("\n--- File System Demo ---")
    fs_helper = FileSystemHelper(dbutils)
    fs_helper.ensure_path_exists("/mnt/raw/2024/06/15/")

    print("\n--- Secret Demo ---")
    os.environ["DBSECRET_PROD_DB_PASSWORD"] = "super-secret-123"  # Test only
    creds = SecureCredentialLoader(dbutils, scope="prod")
    password = creds.get("db-password")
    print(f"Secret retrieved (never log this): [REDACTED] | len={len(password)}")
