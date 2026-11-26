"""
================================================================================
MODULE 17: DateTime, Timestamps & UTC Partitioning
================================================================================
1. EXPLANATION:
Date and time operations structure partition paths (`year=YYYY/month=MM/day=DD`) and calculate SLAs.
Always use explicit UTC timezone (`datetime.now(timezone.utc)`).

2. BUSINESS USE CASE:
Format ISO timestamps and construct S3/ADLS partition paths.
"""
from datetime import datetime, timezone

def generate_partition_path(ts: datetime = None) -> str:
    """Generate partition path string in format 'year=YYYY/month=MM/day=DD'."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    return ts.strftime("year=%Y/month=%m/day=%d")

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    print("ISO UTC Timestamp:", now.isoformat())
    print("Partition Path:", generate_partition_path(now))
