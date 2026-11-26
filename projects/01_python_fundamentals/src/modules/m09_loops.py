"""
================================================================================
MODULE 09: Loops & Iteration Strategies
================================================================================
1. EXPLANATION:
Loops iterate over collections or streams. `while` loops handle retry logic and polling,
while `for` loops iterate over batch data.

2. BUSINESS USE CASE:
Poll a simulated external API until data becomes available or max retries are exceeded.
"""
import time
from typing import Optional, Dict

def poll_job_status(max_attempts: int = 3) -> Optional[Dict[str, str]]:
    """Poll job status with retry attempt counter."""
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        # Simulated check
        if attempt == 2:
            return {"status": "SUCCESS", "job_id": "JOB100"}
        time.sleep(0.1)
    return None

if __name__ == "__main__":
    status = poll_job_status()
    print("Polled Status:", status)
