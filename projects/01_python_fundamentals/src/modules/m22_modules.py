"""
================================================================================
MODULE 22: Python Modules & Namespace Importation
================================================================================
1. EXPLANATION:
Modules (.py files) organize helper utility functions and data pipeline components.

2. BUSINESS USE CASE:
Demonstrate importing custom functions across pipeline modules.
"""
from typing import List

def calculate_checksum(data: List[int]) -> int:
    """Calculate simple sum checksum for record verification."""
    return sum(data)
