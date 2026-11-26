"""
================================================================================
MODULE 45: Mini ETL Project Orchestrator
================================================================================
1. EXPLANATION:
Integrates all 44 preceding modules into a single, cohesive, production-grade ETL orchestrator.

2. BUSINESS USE CASE:
Extracts CSV sales data, validates records, cleans nulls, transforms aggregates, and loads JSON summary.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(current_dir))

from pipeline.main_etl import run_pipeline

if __name__ == "__main__":
    p01_root = current_dir.parent
    status = run_pipeline(p01_root)
    print(f"Mini ETL Pipeline execution finished with status code {status}.")
