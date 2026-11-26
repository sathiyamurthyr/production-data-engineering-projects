"""
================================================================================
MODULE 38: OS Module & System Interaction
================================================================================
1. EXPLANATION:
The `os` module interacts with the host operating system, environment variables, and process paths.

2. BUSINESS USE CASE:
Inspect CPU core count and current working directory for parallelism setup.
"""
import os

def get_system_metadata():
    """Retrieve OS environment metadata."""
    return {
        "cpu_count": os.cpu_count(),
        "cwd": os.getcwd(),
        "pid": os.getpid()
    }

if __name__ == "__main__":
    print("System Metadata:", get_system_metadata())
