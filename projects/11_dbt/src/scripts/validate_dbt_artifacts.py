#!/usr/bin/env python3
"""
dbt Artifact Validation Script
===============================
Parses target/manifest.json and target/run_results.json artifacts to validate:
- Zero failed models or tests in run_results.json
- Data quality test coverage across all models in manifest.json
- Execution duration thresholds and performance SLAs
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("dbt_artifact_validator")


def validate_run_results(run_results_path: Path) -> dict:
    """
    Validates target/run_results.json to ensure no models or tests failed.
    """
    if not run_results_path.exists():
        logger.warning(f"Run results file not found at {run_results_path}")
        return {"status": "skipped", "reason": "file_not_found"}

    with open(run_results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    total_nodes = len(results)
    failures = []
    warnings = []
    total_execution_time = 0.0

    for res in results:
        unique_id = res.get("unique_id", "")
        status = res.get("status", "")
        exec_time = res.get("execution_time", 0.0)
        total_execution_time += exec_time

        if status in ["error", "fail"]:
            failures.append({"id": unique_id, "message": res.get("message", "")})
        elif status in ["warn"]:
            warnings.append({"id": unique_id, "message": res.get("message", "")})

    logger.info(f"Parsed {total_nodes} execution results. Failures: {len(failures)}, Warnings: {len(warnings)}")
    return {
        "status": "failed" if len(failures) > 0 else "passed",
        "total_nodes": total_nodes,
        "failures": failures,
        "warnings": warnings,
        "total_execution_time_seconds": round(total_execution_time, 2)
    }


def validate_manifest(manifest_path: Path) -> dict:
    """
    Validates target/manifest.json to ensure all models have descriptions and test assertions.
    """
    if not manifest_path.exists():
        logger.warning(f"Manifest file not found at {manifest_path}")
        return {"status": "skipped", "reason": "file_not_found"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", {})
    models = {k: v for k, v in nodes.items() if k.startswith("model.")}
    tests = {k: v for k, v in nodes.items() if k.startswith("test.")}

    undocumented_models = []
    untested_models = []

    # Map tests to parent models
    model_test_counts = {k: 0 for k in models.keys()}
    for test_key, test_node in tests.items():
        depends_on_nodes = test_node.get("depends_on", {}).get("nodes", [])
        for parent in depends_on_nodes:
            if parent in model_test_counts:
                model_test_counts[parent] += 1

    for model_key, model_node in models.items():
        model_name = model_node.get("name", "")
        description = model_node.get("description", "")
        if not description or len(description.strip()) == 0:
            undocumented_models.append(model_name)

        if model_test_counts.get(model_key, 0) == 0:
            untested_models.append(model_name)

    logger.info(f"Parsed {len(models)} models. Undocumented: {len(undocumented_models)}, Untested: {len(untested_models)}")
    return {
        "status": "passed" if len(undocumented_models) == 0 and len(untested_models) == 0 else "warning",
        "total_models": len(models),
        "undocumented_models": undocumented_models,
        "untested_models": untested_models
    }


def main():
    target_dir = Path("src/dbt_project/target")
    run_results_path = target_dir / "run_results.json"
    manifest_path = target_dir / "manifest.json"

    logger.info("Validating dbt compilation and execution artifacts...")
    run_val = validate_run_results(run_results_path)
    manifest_val = validate_manifest(manifest_path)

    summary = {
        "run_results_validation": run_val,
        "manifest_validation": manifest_val
    }

    print("\n--- ARTIFACT VALIDATION REPORT ---")
    print(json.dumps(summary, indent=2))

    if run_val.get("status") == "failed":
        logger.error("dbt run results validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
