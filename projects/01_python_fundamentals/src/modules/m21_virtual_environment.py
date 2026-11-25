"""
================================================================================
MODULE 21: Virtual Environments & Dependency Isolation
================================================================================
1. EXPLANATION:
Virtual environments (`venv`) isolate python dependencies per project, avoiding version conflicts.

2. BUSINESS USE CASE:
Inspect active virtual environment state programmatically.
"""
import sys

def check_virtual_environment() -> bool:
    """Return True if code is running inside a virtual environment."""
    return sys.prefix != sys.base_prefix

if __name__ == "__main__":
    print("Is Running in Virtual Env:", check_virtual_environment())
