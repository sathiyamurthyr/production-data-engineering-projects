"""
================================================================================
MODULE 32: HTTP API Requests & Status Handling
================================================================================
1. EXPLANATION:
Extract data from web services using HTTP requests, verifying response codes (`200 OK`, `429 Rate Limited`).

2. BUSINESS USE CASE:
Fetch JSON payloads from public REST APIs safely.
"""
from typing import Dict, Any, Optional
import urllib.request
import json

def fetch_json_api(url: str) -> Optional[Dict[str, Any]]:
    """Fetch JSON payload using standard urllib."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DE-Pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"API fetch error: {e}")
    return None
