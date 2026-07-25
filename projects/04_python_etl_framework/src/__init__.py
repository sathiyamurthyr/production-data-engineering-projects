"""
Enterprise Python ETL Framework

A production-ready, modular ETL framework for data engineering teams.
"""

__version__ = "1.0.0"
__author__ = "Sathiya Murthy"

from etl_framework.core.pipeline import Pipeline
from etl_framework.core.context import ExecutionContext

__all__ = ["Pipeline", "ExecutionContext"]