"""
================================================================================
MODULE 20: Environment Variables & Secrets Safety
================================================================================
1. EXPLANATION:
Environment variables inject database credentials, API keys, and environment modes without hardcoding.

2. BUSINESS USE CASE:
Inject database connection strings dynamically from system env vars.
"""
import os
from typing import Dict

def get_database_credentials() -> Dict[str, str]:
    """Retrieve database credentials safely from environment variables."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD", "secret_pass")
    }

if __name__ == "__main__":
    creds = get_database_credentials()
    print(f"DB Credentials Loaded (Host: {creds['host']}, User: {creds['user']})")
