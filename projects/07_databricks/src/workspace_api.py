"""
Module 02: Workspace API — Databricks REST API Patterns
=======================================================

Explanation:
    The Databricks REST API provides programmatic access to all workspace resources:
    clusters, jobs, notebooks, files, DBFS, secrets, SQL warehouses, and Unity Catalog.
    The Databricks Python SDK wraps these APIs with type safety and automatic pagination.

Business Use Case:
    - Monitoring cluster health and utilization dashboards
    - Automated job creation and scheduling from CI/CD pipelines
    - Workspace auditing: listing all notebooks, jobs, and permissions
    - Cost allocation: querying cluster usage by team/project
    - Self-service cluster provisioning via internal developer portals

Production Example:
    A platform engineering team uses workspace_api.py in a Lambda function
    triggered every 15 minutes to terminate any cluster idle for > 60 minutes,
    saving ~40% on compute costs.

Performance Notes:
    - The SDK handles API rate limiting with exponential backoff automatically
    - Use list() with pagination (max_results) for large workspaces (1000s of jobs)
    - Cache cluster lists locally for dashboards to avoid hammering the API
    - Use async API calls for parallel workspace operations

Common Mistakes:
    - Using requests directly instead of the SDK (loses retry logic, type safety)
    - Not handling pagination — list APIs return at most 100 results by default
    - Ignoring rate limit errors (HTTP 429) in production scripts
    - Polling job state in tight loops (use wait_for_run instead)

Interview Questions:
    Q: What is the difference between the Databricks REST API and the SDK?
    A: The REST API is the underlying HTTP interface. The SDK wraps it with
       Python type hints, automatic pagination, retry with backoff, and
       strongly-typed response objects. Always prefer the SDK in new code.

    Q: How do you monitor a Databricks job run programmatically?
    A: Use sdk.jobs.wait_for_run(run_id) which polls the run state and returns
       when the run completes (success or failure). Use run.state.result_state
       to check the outcome.

    Q: How would you implement workspace auditing at scale?
    A: List all clusters, jobs, and notebooks using SDK pagination, enrich
       with access-control (permissions API), and export to a Delta table
       for audit trail queries.

Author: Sathiya Murthy
Blog: Data Engineering Diaries
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

try:
    import requests
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service import compute, jobs
    from databricks.sdk.service.compute import ClusterDetails, State
    from databricks.sdk.service.jobs import Run, RunState, RunResultState
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    WorkspaceClient = None  # type: ignore[misc,assignment]


# ─────────────────────────────────────────────────────────────────────────────
# Data Transfer Objects
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClusterSummary:
    """Lightweight cluster summary for dashboards and cost reporting."""
    cluster_id: str
    cluster_name: str
    state: str
    driver_node_type: str
    worker_count: int
    spark_version: str
    creator: Optional[str]
    created_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    autotermination_minutes: Optional[int]

    @property
    def is_running(self) -> bool:
        return self.state == "RUNNING"

    @property
    def is_idle(self) -> bool:
        """Cluster is running but has been inactive for an extended period."""
        if not self.last_activity_at or not self.is_running:
            return False
        idle_minutes = (datetime.utcnow() - self.last_activity_at).total_seconds() / 60
        return idle_minutes > (self.autotermination_minutes or 60)


@dataclass
class JobSummary:
    """Lightweight job summary for pipeline inventory."""
    job_id: int
    job_name: str
    creator_user_name: Optional[str]
    schedule_quartz_cron: Optional[str]
    max_concurrent_runs: int
    last_run_status: Optional[str]


@dataclass
class RunSummary:
    """Summary of a job run for monitoring and alerting."""
    run_id: int
    job_id: int
    run_name: str
    state: str
    result_state: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[float]

    @property
    def succeeded(self) -> bool:
        return self.result_state == "SUCCESS"

    @property
    def failed(self) -> bool:
        return self.result_state in ("FAILED", "TIMEDOUT", "CANCELED")


# ─────────────────────────────────────────────────────────────────────────────
# DatabricksWorkspaceClient
# ─────────────────────────────────────────────────────────────────────────────

class DatabricksWorkspaceClient:
    """
    High-level Databricks workspace client for production operations.

    Wraps the Databricks SDK with domain-specific methods for cluster
    management, job operations, and workspace auditing.

    Usage:
        client = DatabricksWorkspaceClient.from_env()

        # List running clusters
        for cluster in client.list_clusters(state_filter="RUNNING"):
            print(f"{cluster.cluster_name}: {cluster.state}")

        # Trigger a job and wait for completion
        run_id = client.trigger_job(job_id=12345)
        result = client.wait_for_run(run_id, timeout_minutes=60)
        print(f"Job result: {result.result_state}")
    """

    def __init__(self, workspace_client: "WorkspaceClient") -> None:
        self._wc = workspace_client
        log.info("DatabricksWorkspaceClient initialized")

    @classmethod
    def from_env(cls) -> "DatabricksWorkspaceClient":
        """Create client from DATABRICKS_HOST and DATABRICKS_TOKEN env vars."""
        if not HAS_SDK:
            raise ImportError("Install databricks-sdk: pip install databricks-sdk")
        wc = WorkspaceClient(
            host=os.environ["DATABRICKS_HOST"],
            token=os.environ["DATABRICKS_TOKEN"],
        )
        return cls(wc)

    @classmethod
    def from_client(cls, wc: "WorkspaceClient") -> "DatabricksWorkspaceClient":
        """Create from an existing SDK WorkspaceClient (for injection in tests)."""
        return cls(wc)

    # ─────────────────────────────────────────────────────────────────────────
    # Cluster Operations
    # ─────────────────────────────────────────────────────────────────────────

    def list_clusters(
        self,
        state_filter: Optional[str] = None,
        name_prefix: Optional[str] = None,
    ) -> List[ClusterSummary]:
        """
        List all clusters in the workspace with optional filtering.

        Args:
            state_filter: Filter by state — "RUNNING", "TERMINATED", "PENDING", etc.
            name_prefix: Filter clusters whose name starts with this prefix.

        Returns:
            List of ClusterSummary objects, sorted by name.
        """
        summaries = []
        for cluster in self._wc.clusters.list():
            state = cluster.state.value if cluster.state else "UNKNOWN"

            if state_filter and state != state_filter:
                continue
            if name_prefix and not (cluster.cluster_name or "").startswith(name_prefix):
                continue

            # Parse last activity timestamp (milliseconds epoch)
            last_activity = None
            if cluster.last_activity_time:
                last_activity = datetime.utcfromtimestamp(cluster.last_activity_time / 1000)

            created_at = None
            if cluster.start_time:
                created_at = datetime.utcfromtimestamp(cluster.start_time / 1000)

            summaries.append(ClusterSummary(
                cluster_id=cluster.cluster_id or "",
                cluster_name=cluster.cluster_name or "unnamed",
                state=state,
                driver_node_type=cluster.driver_node_type_id or "unknown",
                worker_count=cluster.num_workers or 0,
                spark_version=cluster.spark_version or "unknown",
                creator=cluster.creator_user_name,
                created_at=created_at,
                last_activity_at=last_activity,
                autotermination_minutes=cluster.autotermination_minutes,
            ))

        summaries.sort(key=lambda c: c.cluster_name)
        log.info("Found %d clusters (filter: state=%s, prefix=%s)",
                 len(summaries), state_filter, name_prefix)
        return summaries

    def get_cluster(self, cluster_id: str) -> ClusterSummary:
        """Get details for a specific cluster by ID."""
        cluster = self._wc.clusters.get(cluster_id=cluster_id)
        state = cluster.state.value if cluster.state else "UNKNOWN"
        return ClusterSummary(
            cluster_id=cluster.cluster_id or "",
            cluster_name=cluster.cluster_name or "unnamed",
            state=state,
            driver_node_type=cluster.driver_node_type_id or "unknown",
            worker_count=cluster.num_workers or 0,
            spark_version=cluster.spark_version or "unknown",
            creator=cluster.creator_user_name,
            created_at=None,
            last_activity_at=None,
            autotermination_minutes=cluster.autotermination_minutes,
        )

    def terminate_idle_clusters(
        self,
        idle_threshold_minutes: int = 60,
        dry_run: bool = True,
    ) -> List[str]:
        """
        Find and optionally terminate clusters that have been idle too long.

        This is a common FinOps (cloud cost management) automation pattern.

        Args:
            idle_threshold_minutes: Minutes of inactivity before considering idle.
            dry_run: If True, log but don't terminate clusters.

        Returns:
            List of cluster IDs that were (or would be) terminated.
        """
        terminated_ids = []
        running_clusters = self.list_clusters(state_filter="RUNNING")

        for cluster in running_clusters:
            if not cluster.last_activity_at:
                continue
            idle_mins = (datetime.utcnow() - cluster.last_activity_at).total_seconds() / 60
            if idle_mins > idle_threshold_minutes:
                log.info(
                    "Idle cluster detected | id=%s | name=%s | idle=%.1f min",
                    cluster.cluster_id, cluster.cluster_name, idle_mins
                )
                if not dry_run:
                    self._wc.clusters.delete(cluster_id=cluster.cluster_id)
                    log.info("Terminated cluster: %s", cluster.cluster_id)
                terminated_ids.append(cluster.cluster_id)

        mode = "DRY RUN" if dry_run else "LIVE"
        log.info("[%s] Would terminate %d idle clusters", mode, len(terminated_ids))
        return terminated_ids

    # ─────────────────────────────────────────────────────────────────────────
    # Job Operations
    # ─────────────────────────────────────────────────────────────────────────

    def list_jobs(self, name_prefix: Optional[str] = None) -> List[JobSummary]:
        """
        List all jobs in the workspace with an optional name filter.

        Args:
            name_prefix: Filter jobs by name prefix.

        Returns:
            List of JobSummary objects.
        """
        summaries = []
        for job in self._wc.jobs.list():
            name = job.settings.name if job.settings else "unnamed"
            if name_prefix and not name.startswith(name_prefix):
                continue

            schedule_cron = None
            if job.settings and job.settings.schedule:
                schedule_cron = job.settings.schedule.quartz_cron_expression

            summaries.append(JobSummary(
                job_id=job.job_id or 0,
                job_name=name,
                creator_user_name=job.creator_user_name,
                schedule_quartz_cron=schedule_cron,
                max_concurrent_runs=job.settings.max_concurrent_runs if job.settings else 1,
                last_run_status=None,   # Requires separate API call
            ))

        log.info("Found %d jobs", len(summaries))
        return summaries

    def trigger_job(
        self,
        job_id: int,
        notebook_params: Optional[dict] = None,
        python_params: Optional[list] = None,
    ) -> int:
        """
        Trigger a job run with optional parameter overrides.

        Args:
            job_id: Databricks job ID.
            notebook_params: Key-value pairs passed to notebook widgets.
            python_params: List of string params passed to Python task.

        Returns:
            int: The run_id of the triggered run.
        """
        run = self._wc.jobs.run_now(
            job_id=job_id,
            notebook_params=notebook_params,
            python_params=python_params,
        )
        run_id = run.run_id
        log.info("Job triggered | job_id=%d | run_id=%d", job_id, run_id)
        return run_id

    def wait_for_run(
        self,
        run_id: int,
        timeout_minutes: int = 120,
        poll_interval_seconds: int = 30,
    ) -> RunSummary:
        """
        Poll a job run until completion and return the result.

        Production pattern: use this in CI/CD pipelines to block until
        a Databricks job finishes and fail the pipeline on job failure.

        Args:
            run_id: The run ID to monitor.
            timeout_minutes: Maximum wait time before raising TimeoutError.
            poll_interval_seconds: How frequently to poll the run state.

        Returns:
            RunSummary with final run state.

        Raises:
            TimeoutError: If the run doesn't complete within timeout_minutes.
        """
        deadline = time.time() + (timeout_minutes * 60)
        log.info("Waiting for run_id=%d (timeout=%d min)", run_id, timeout_minutes)

        while time.time() < deadline:
            run = self._wc.jobs.get_run(run_id=run_id)
            state_value = run.state.life_cycle_state.value if run.state and run.state.life_cycle_state else "UNKNOWN"
            result_state = None
            if run.state and run.state.result_state:
                result_state = run.state.result_state.value

            log.info("Run %d | lifecycle=%s | result=%s", run_id, state_value, result_state)

            # Terminal states
            if state_value in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
                start_ms = run.start_time or 0
                end_ms = run.end_time or 0
                duration = (end_ms - start_ms) / 1000 if start_ms and end_ms else None
                return RunSummary(
                    run_id=run_id,
                    job_id=run.job_id or 0,
                    run_name=run.run_name or "",
                    state=state_value,
                    result_state=result_state,
                    start_time=datetime.utcfromtimestamp(start_ms / 1000) if start_ms else None,
                    end_time=datetime.utcfromtimestamp(end_ms / 1000) if end_ms else None,
                    duration_seconds=duration,
                )

            time.sleep(poll_interval_seconds)

        raise TimeoutError(
            f"Run {run_id} did not complete within {timeout_minutes} minutes. "
            "Check Databricks UI for details."
        )

    def get_recent_runs(
        self,
        job_id: int,
        limit: int = 10,
    ) -> List[RunSummary]:
        """
        Get the most recent runs for a job.

        Useful for building run history dashboards and detecting flapping jobs.

        Args:
            job_id: Databricks job ID.
            limit: Maximum number of runs to return.

        Returns:
            List of RunSummary objects, most recent first.
        """
        summaries = []
        for run in self._wc.jobs.list_runs(job_id=job_id, limit=limit):
            state_value = run.state.life_cycle_state.value if run.state and run.state.life_cycle_state else "UNKNOWN"
            result_state = run.state.result_state.value if run.state and run.state.result_state else None
            start_ms = run.start_time or 0
            end_ms = run.end_time or 0
            summaries.append(RunSummary(
                run_id=run.run_id or 0,
                job_id=job_id,
                run_name=run.run_name or "",
                state=state_value,
                result_state=result_state,
                start_time=datetime.utcfromtimestamp(start_ms / 1000) if start_ms else None,
                end_time=datetime.utcfromtimestamp(end_ms / 1000) if end_ms else None,
                duration_seconds=(end_ms - start_ms) / 1000 if start_ms and end_ms else None,
            ))
        return summaries

    # ─────────────────────────────────────────────────────────────────────────
    # Notebook Operations
    # ─────────────────────────────────────────────────────────────────────────

    def list_notebooks(self, path: str = "/") -> List[dict]:
        """
        Recursively list all notebooks under a workspace path.

        Args:
            path: Workspace path to search (e.g., "/Users/team@company.com").

        Returns:
            List of dicts with notebook path, language, and size.
        """
        notebooks = []
        try:
            items = self._wc.workspace.list(path=path)
            if items:
                for item in items:
                    if item.object_type and item.object_type.value == "NOTEBOOK":
                        notebooks.append({
                            "path": item.path,
                            "language": item.language.value if item.language else "unknown",
                            "size_bytes": item.size or 0,
                        })
                    elif item.object_type and item.object_type.value == "DIRECTORY":
                        # Recursive descent into subdirectories
                        notebooks.extend(self.list_notebooks(path=item.path))
        except Exception as exc:
            log.warning("Error listing notebooks at %s: %s", path, exc)

        return notebooks

    # ─────────────────────────────────────────────────────────────────────────
    # Workspace Audit
    # ─────────────────────────────────────────────────────────────────────────

    def audit_workspace(self) -> dict:
        """
        Generate a comprehensive workspace inventory for auditing.

        Returns:
            dict with counts and details of workspace resources.
        """
        log.info("Starting workspace audit...")

        clusters = self.list_clusters()
        running = [c for c in clusters if c.is_running]

        jobs_list = self.list_jobs()

        audit = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "workspace_url": self._wc.config.host,
            "clusters": {
                "total": len(clusters),
                "running": len(running),
                "terminated": len([c for c in clusters if c.state == "TERMINATED"]),
                "details": [
                    {
                        "id": c.cluster_id,
                        "name": c.cluster_name,
                        "state": c.state,
                        "creator": c.creator,
                    }
                    for c in clusters
                ],
            },
            "jobs": {
                "total": len(jobs_list),
                "scheduled": len([j for j in jobs_list if j.schedule_quartz_cron]),
                "details": [
                    {
                        "id": j.job_id,
                        "name": j.job_name,
                        "creator": j.creator_user_name,
                        "schedule": j.schedule_quartz_cron,
                    }
                    for j in jobs_list
                ],
            },
        }

        log.info(
            "Audit complete | clusters=%d (%d running) | jobs=%d",
            audit["clusters"]["total"],
            audit["clusters"]["running"],
            audit["jobs"]["total"],
        )
        return audit


# ─────────────────────────────────────────────────────────────────────────────
# Raw REST API pattern (for reference — prefer SDK over this)
# ─────────────────────────────────────────────────────────────────────────────

class DatabricksRawAPIClient:
    """
    Low-level REST API client using requests library.

    Use this as a REFERENCE ONLY. The Databricks SDK is strongly preferred
    in production because it handles:
        - Authentication token refresh
        - Automatic pagination
        - Retry with exponential backoff
        - API versioning
        - Type-safe response parsing
    """

    def __init__(self, host: str, token: str) -> None:
        self._host = host.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to the Databricks REST API."""
        url = f"{self._host}/api/2.1/{endpoint}"
        resp = requests.get(url, headers=self._headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, payload: dict) -> dict:
        """Make a POST request to the Databricks REST API."""
        url = f"{self._host}/api/2.1/{endpoint}"
        resp = requests.post(url, headers=self._headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_clusters_raw(self) -> list:
        """List clusters using raw REST API (educational reference)."""
        return self._get("clusters/list").get("clusters", [])

    def run_job_raw(self, job_id: int) -> int:
        """Trigger a job run and return the run_id."""
        result = self._post("jobs/run-now", {"job_id": job_id})
        return result["run_id"]


if __name__ == "__main__":
    print("Module 02: Workspace API")
    print("Set DATABRICKS_HOST and DATABRICKS_TOKEN to use live workspace features.")

    if os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN"):
        client = DatabricksWorkspaceClient.from_env()
        audit = client.audit_workspace()
        print(f"Workspace Audit:")
        print(f"  Clusters: {audit['clusters']['total']} total, {audit['clusters']['running']} running")
        print(f"  Jobs: {audit['jobs']['total']} total, {audit['jobs']['scheduled']} scheduled")
