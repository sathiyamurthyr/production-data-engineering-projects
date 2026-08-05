#!/usr/bin/env python3
"""Validate that all patterns have required files.

This script checks that every pattern directory contains all required files
as specified in the contribution guidelines.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "README.md",
    "architecture.md",
    "implementation.md",
    "decision-matrix.md",
    "anti-patterns.md",
    "performance.md",
    "security.md",
    "operations.md",
    "cost-analysis.md",
    "deployment-guide.md",
    "troubleshooting.md",
    "interview-questions.md",
    "requirements.txt",
]

REQUIRED_DIRS = [
    "src",
    "tests",
    "benchmarks",
    "datasets",
    "mermaid",
]

REQUIRED_PATTERN_FILES = REQUIRED_FILES + [
    "src/__init__.py",
    "tests/__init__.py",
    "mermaid/architecture.mmd",
]

PATTERN_CATEGORIES = [
    "architecture-patterns",
    "ingestion-patterns",
    "etl-patterns",
    "elt-patterns",
    "cdc-patterns",
    "streaming-patterns",
    "spark-patterns",
    "delta-patterns",
    "databricks-patterns",
    "airflow-patterns",
    "kafka-patterns",
    "snowflake-patterns",
    "dbt-patterns",
    "lakehouse-patterns",
    "metadata-patterns",
    "governance-patterns",
    "quality-patterns",
    "observability-patterns",
    "security-patterns",
    "platform-patterns",
    "ai-patterns",
    "mlops-patterns",
    "rag-patterns",
    "agent-patterns",
    "multicloud-patterns",
    "sre-patterns",
    "finops-patterns",
    "devops-patterns",
]


def validate_pattern(pattern_dir: Path) -> list[str]:
    """Validate a single pattern directory.

    Args:
        pattern_dir: Path to the pattern directory.

    Returns:
        List of missing files/directories.
    """
    missing: list[str] = []

    for req_file in REQUIRED_PATTERN_FILES:
        file_path = pattern_dir / req_file
        if not file_path.exists():
            missing.append(req_file)

    for req_dir in REQUIRED_DIRS:
        dir_path = pattern_dir / req_dir
        if not dir_path.exists():
            missing.append(f"{req_dir}/ (dir)")

    return missing


def main() -> int:
    """Run pattern validation.

    Returns:
        Exit code: 0 if all valid, 1 if any missing files.
    """
    total_patterns = 0
    total_missing = 0

    for category in PATTERN_CATEGORIES:
        category_path = REPO_ROOT / category
        if not category_path.exists():
            print(f"  [SKIP] {category}/ (directory not found)")
            continue

        patterns = sorted(
            d for d in category_path.iterdir() if d.is_dir()
        )

        if not patterns:
            print(f"  [SKIP] {category}/ (no patterns)")
            continue

        print(f"\n[Category] {category}/")

        for pattern in patterns:
            total_patterns += 1
            missing = validate_pattern(pattern)

            if missing:
                total_missing += len(missing)
                print(f"  [WARN] {pattern.name}/ - missing: {', '.join(missing)}")
            else:
                print(f"  [OK]   {pattern.name}/")

    print(f"\n{'='*60}")
    print(f"Total patterns found: {total_patterns}")
    print(f"Total missing files: {total_missing}")

    if total_missing > 0:
        print("RESULT: VALIDATION FAILED - Some patterns have missing files.")
        return 1
    else:
        print("RESULT: ALL PATTERNS VALID ✅")
        return 0


if __name__ == "__main__":
    sys.exit(main())
