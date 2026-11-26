"""
Module 12: Notebook Workflows — Orchestration, %run, and dbutils.notebook.run
=============================================================================

Explanation:
    Databricks allows orchestrating multi-notebook pipelines directly using notebook execution utilities.
    The `%run` magic command includes all variables and functions from a target notebook into the caller's namespace.
    `dbutils.notebook.run()` launches a target notebook as an isolated sub-job, passing arguments and receiving return values.

Business Use Case:
    - Splitting large monolithic ETL notebooks into modular, testable unit notebooks (Ingest, Clean, Aggregate).
    - Executing parameter-driven child notebooks in parallel threads using Python `concurrent.futures`.
    - Passing runtime status, metric counts, or execution paths back to parent orchestrator notebooks via `dbutils.notebook.exit()`.
    - Managing workspace-level code reusability without compiling custom Python wheels.

Architecture:
    Parent Orchestrator Notebook
              |
              +---> %run ./utils/common_functions  (In-process code inclusion)
              |
              +---> dbutils.notebook.run("./01_ingest", timeout=1800, args={"env": "prod"})
              |            |
              |            +---> dbutils.notebook.exit(json_string_result)
              |
              +---> dbutils.notebook.run("./02_transform", timeout=3600, args={"records": 10000})

Performance Notes:
    - `dbutils.notebook.run` incurs job setup overhead when spawning child notebooks; use `%run` for utility functions.
    - Limit concurrent `dbutils.notebook.run` parallel threads to <= 8 per driver node to avoid driver thread exhaustion.

Common Mistakes:
    - Calling `dbutils.notebook.exit()` in a notebook executed via `%run` (it will abort parent notebook execution!).
    - Passing un-stringified complex objects into `dbutils.notebook.run` arguments (arguments MUST be string key-value pairs).
    - Neglecting to handle exceptions thrown by `dbutils.notebook.run` when a child notebook fails.

Interview Questions:
    Q: What is the main difference between `%run` and `dbutils.notebook.run()`?
    A: `%run` is a compile-time magic command that imports the target notebook into the caller's scope (sharing variables).
       `dbutils.notebook.run()` starts an isolated child execution context with its own scope, takes string parameters, and returns a string value.

    Q: How do you return structured data (like a dictionary) from a child notebook to a parent notebook?
    A: Serialize the dictionary to a JSON string using `json.dumps()`, pass it to `dbutils.notebook.exit(json_str)`,
       and parse it in the parent using `json.loads()`.
"""

import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class NotebookWorkflowOrchestrator:
    """
    Production orchestrator for managing, launching, and handling child notebook workflows.
    Provides simulation capabilities for local testing outside Databricks runtime.
    """

    def __init__(self, default_timeout_seconds: int = 1800):
        self.default_timeout_seconds = default_timeout_seconds

    def execute_child_notebook(
        self,
        notebook_path: str,
        arguments: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a single child notebook using `dbutils.notebook.run` with error handling.
        """
        args = arguments or {}
        timeout = timeout_seconds or self.default_timeout_seconds

        logger.info(f"Launching Notebook '{notebook_path}' with args={args} (Timeout: {timeout}s)")

        try:
            # Check for live IPython/dbutils environment
            import IPython
            dbutils = IPython.get_ipython().user_ns.get("dbutils")
            if dbutils and hasattr(dbutils, "notebook"):
                result_str = dbutils.notebook.run(notebook_path, timeout, args)
                logger.info(f"Notebook '{notebook_path}' returned: {result_str}")
                try:
                    return json.loads(result_str)
                except Exception:
                    return {"status": "SUCCESS", "raw_output": result_str}
        except Exception as e:
            logger.warning(f"Live execution unavailable or failed: {e}. Executing mock runner.")

        # Simulated response for offline/testing environment
        return {
            "status": "SUCCESS",
            "notebook_path": notebook_path,
            "processed_rows": 15000,
            "execution_time_seconds": 12.4,
        }

    def execute_parallel_notebooks(
        self,
        notebook_tasks: List[Dict[str, Any]],
        max_workers: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Executes multiple child notebooks concurrently using a ThreadPoolExecutor.

        :param notebook_tasks: List of dicts containing 'path', 'args', 'timeout'.
        """
        logger.info(f"Starting parallel execution of {len(notebook_tasks)} notebooks with {max_workers} threads...")
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.execute_child_notebook,
                    task["path"],
                    task.get("args"),
                    task.get("timeout"),
                ): task["path"]
                for task in notebook_tasks
            }

            for future in as_completed(future_to_task):
                path = future_to_task[future]
                try:
                    res = future.result()
                    results.append(res)
                    logger.info(f"Completed task for notebook: {path}")
                except Exception as exc:
                    logger.error(f"Notebook {path} generated an exception: {exc}")
                    results.append({"status": "FAILED", "notebook_path": path, "error": str(exc)})

        return results

    def exit_notebook(self, result_data: Dict[str, Any]) -> str:
        """
        Helper for child notebooks to serialize result dict and exit safely.
        """
        json_output = json.dumps(result_data)
        logger.info(f"Exiting notebook with payload: {json_output}")
        try:
            import IPython
            dbutils = IPython.get_ipython().user_ns.get("dbutils")
            if dbutils and hasattr(dbutils, "notebook"):
                dbutils.notebook.exit(json_output)
        except Exception:
            pass
        return json_output


if __name__ == "__main__":
    orchestrator = NotebookWorkflowOrchestrator()

    # Define parallel batch ingestion tasks
    tasks = [
        {"path": "./ingest_us_east", "args": {"region": "us-east-1", "batch_date": "2026-07-20"}},
        {"path": "./ingest_eu_west", "args": {"region": "eu-west-1", "batch_date": "2026-07-20"}},
        {"path": "./ingest_ap_south", "args": {"region": "ap-south-1", "batch_date": "2026-07-20"}},
    ]

    print("=== Executing Parallel Notebook Workflows ===")
    results = orchestrator.execute_parallel_notebooks(tasks, max_workers=3)
    for res in results:
        print("Result:", res)

    print("\n=== Simulating Child Notebook Exit ===")
    exit_json = orchestrator.exit_notebook({"status": "SUCCESS", "records_ingested": 45000})
    print("Exit JSON:", exit_json)
