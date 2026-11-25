"""
Pipeline Loader Module.
Writes analytical outputs to CSV / JSON targets.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("pipeline.loader")

class DataLoader:
    """Loads metrics into analytical destination files."""

    def load_summary_json(self, summary_data: Dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"Successfully loaded summary metrics to {output_path}")
