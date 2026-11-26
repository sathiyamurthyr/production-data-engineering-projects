"""
Pipeline Data Transformation Engine.
Standardizes data types, computes aggregated KPIs, and transforms schemas.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("pipeline.transformer")

class DataTransformer:
    """Transforms raw transaction records into analytical metrics."""

    def transform_sales(self, valid_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not valid_records:
            return {"category_summary": {}, "total_revenue": 0.0, "processed_count": 0}

        category_summary: Dict[str, float] = {}
        total_revenue = 0.0

        for rec in valid_records:
            category = str(rec.get("product_category", "Uncategorized")).strip().title()
            amount = float(rec["amount"])

            category_summary[category] = category_summary.get(category, 0.0) + amount
            total_revenue += amount

        logger.info(f"Transformed sales data across {len(category_summary)} categories.")
        return {
            "category_summary": category_summary,
            "total_revenue": round(total_revenue, 2),
            "processed_count": len(valid_records)
        }
