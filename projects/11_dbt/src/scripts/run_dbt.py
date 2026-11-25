#!/usr/bin/env python3
"""
Programmatic dbt Runner Script
================================
Executes dbt Core CLI operations programmatically with structured logging,
error handling, execution timing, and JSON output summary reporting.
"""

import argparse
import json
import logging
import os
import sys
import subprocess
import time
from pathlib import Path

# Set up structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dbt_runner")


def run_dbt_command(command: list[str], project_dir: str, profiles_dir: str | None = None) -> tuple[int, str, float]:
    """
    Executes a dbt CLI command using subprocess and logs output cleanly.
    """
    cmd = ["dbt"] + command
    if profiles_dir:
        cmd.extend(["--profiles-dir", profiles_dir])
    
    cmd.extend(["--project-dir", project_dir])
    
    cmd_str = " ".join(cmd)
    logger.info(f"Executing: {cmd_str}")
    
    start_time = time.time()
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        duration = time.time() - start_time
        logger.info(f"Command completed in {duration:.2f}s with status code {process.returncode}")
        return process.returncode, process.stdout, duration
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Execution failed: {str(e)}")
        return 1, str(e), duration


def execute_dbt_pipeline(project_dir: str, target: str = "dev", select: str | None = None) -> dict:
    """
    Executes a standard dbt pipeline sequence: deps -> seed -> snapshot -> run -> test -> docs generate.
    """
    results = {
        "status": "success",
        "target": target,
        "steps": [],
        "total_duration_seconds": 0.0
    }
    
    steps = [
        ["deps"],
        ["seed"],
        ["snapshot"],
        ["run"] + (["--select", select] if select else []),
        ["test"] + (["--select", select] if select else []),
        ["docs", "generate"]
    ]
    
    total_start = time.time()
    for step in steps:
        cmd_args = step + ["--target", target]
        return_code, stdout, duration = run_dbt_command(cmd_args, project_dir)
        
        step_result = {
            "step": step[0],
            "command": " ".join(cmd_args),
            "return_code": return_code,
            "duration_seconds": round(duration, 2)
        }
        results["steps"].append(step_result)
        
        if return_code != 0:
            logger.error(f"Step '{step[0]}' failed with code {return_code}")
            logger.error(stdout[-500:])  # Print tail of output
            results["status"] = "failed"
            break
            
    results["total_duration_seconds"] = round(time.time() - total_start, 2)
    return results


def main():
    parser = argparse.ArgumentParser(description="Programmatic dbt Execution Tool")
    parser.add_argument("--project-dir", type=str, default="src/dbt_project", help="Path to dbt project directory")
    parser.add_argument("--target", type=str, default="dev", help="dbt target profile environment")
    parser.add_argument("--select", type=str, default=None, help="dbt selector expression (e.g. staging, state:modified+)")
    
    args = parser.parse_args()
    
    abs_project_dir = str(Path(args.project_dir).resolve())
    logger.info(f"Starting dbt pipeline run on target={args.target}, project={abs_project_dir}")
    
    summary = execute_dbt_pipeline(abs_project_dir, target=args.target, select=args.select)
    print("\n--- DBT PIPELINE RUN SUMMARY ---")
    print(json.dumps(summary, indent=2))
    
    if summary["status"] != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
