"""
================================================================================
MODULE 19: Configuration File Management (JSON & YAML)
================================================================================
1. EXPLANATION:
Decouple hardcoded constants into YAML or JSON config files.

2. BUSINESS USE CASE:
Load batch sizes, input paths, and retry parameters dynamically from JSON.
"""
import json
from pathlib import Path
from typing import Dict, Any

def load_json_config(config_path: Path) -> Dict[str, Any]:
    """Load JSON config file with fallback defaults."""
    if not config_path.exists():
        return {"batch_size": 1000, "retry_attempts": 3}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
