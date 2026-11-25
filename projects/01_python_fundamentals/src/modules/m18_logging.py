"""
================================================================================
MODULE 18: Structured Logging for Data Pipelines
================================================================================
1. EXPLANATION:
Logging provides real-time audit visibility into pipeline execution without stdout cluttering.

2. BUSINESS USE CASE:
Configure file and console logger handlers for pipeline observability.
"""
import logging
from pathlib import Path

def get_pipeline_logger(name: str) -> logging.Logger:
    """Configure enterprise logger with standard format."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

if __name__ == "__main__":
    log = get_pipeline_logger("sales_ingest")
    log.info("Pipeline started successfully.")
