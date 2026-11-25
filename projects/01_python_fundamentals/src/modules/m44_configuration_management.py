"""
================================================================================
MODULE 44: Dynamic Configuration Management
================================================================================
1. EXPLANATION:
Centralized config managers handle parameter overrides across environments (dev, staging, prod).

2. BUSINESS USE CASE:
Manage settings hierarchy with environment variable overrides.
"""
import os
from typing import Dict, Any

class PipelineConfig:
    """Pipeline Configuration Manager."""
    def __init__(self, defaults: Dict[str, Any]):
        self.config = defaults
        self.config["env"] = os.getenv("PIPELINE_ENV", defaults.get("env", "development"))

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

if __name__ == "__main__":
    cfg = PipelineConfig({"env": "dev", "batch_size": 500})
    print(f"Config Environment: {cfg.get('env')}, Batch Size: {cfg.get('batch_size')}")
