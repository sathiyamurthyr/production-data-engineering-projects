"""
================================================================================
MODULE 40: Subprocess Execution & External CLI Tool Hooks
================================================================================
1. EXPLANATION:
`subprocess.run()` executes system shell commands (e.g. `dbt run`, `spark-submit`, `git`).

2. BUSINESS USE CASE:
Execute external CLI commands safely with timeout and return code verification.
"""
import subprocess
import sys

def execute_cli_command(cmd: list) -> int:
    """Execute external CLI command safely."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode
    except Exception:
        return -1

if __name__ == "__main__":
    code = execute_cli_command([sys.executable, "--version"])
    print("Command Exit Code:", code)
