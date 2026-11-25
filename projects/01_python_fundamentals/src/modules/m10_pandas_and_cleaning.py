"""
Module 35-36, 41-44: Pandas Data Cleaning, Unit Testing & Configuration Management.

Explanation:
Pandas provides vectorized DataFrames for memory-fit data cleaning, missing value imputation,
type enforcement, and KPI aggregations before pushing to staging.

Business Use Case:
Clean raw sales DataFrames, handle null amounts, and aggregate sales per product category.
"""

from typing import Dict, Any, List

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

def clean_and_aggregate_sales(raw_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Clean raw sales records:
    1. Filter out FAILED status records.
    2. Fill or drop missing amounts.
    3. Group by product_category and compute total & mean spend.
    """
    if HAS_PANDAS and isinstance(raw_records, pd.DataFrame):
        df = raw_records
        if df.empty:
            return {}
        cleaned_df = df[df["status"] == "COMPLETED"].copy()
        cleaned_df["amount"] = pd.to_numeric(cleaned_df["amount"], errors="coerce")
        cleaned_df = cleaned_df.dropna(subset=["amount"])
        agg_df = cleaned_df.groupby("product_category")["amount"].agg(["sum", "mean", "count"]).reset_index()
        result = {}
        for _, row in agg_df.iterrows():
            result[row["product_category"]] = {
                "total_sales": float(row["sum"]),
                "avg_sales": float(row["mean"]),
                "count": int(row["count"])
            }
        return result

    # Pure Python Fallback if pandas is absent
    summary: Dict[str, List[float]] = {}
    for rec in raw_records:
        if rec.get("status") != "COMPLETED":
            continue
        try:
            amt = float(rec.get("amount", 0.0))
        except (ValueError, TypeError):
            continue
        cat = str(rec.get("product_category", "Unknown")).strip()
        if cat not in summary:
            summary[cat] = []
        summary[cat].append(amt)

    output = {}
    for cat, amounts in summary.items():
        output[cat] = {
            "total_sales": round(sum(amounts), 2),
            "avg_sales": round(sum(amounts) / len(amounts), 2) if amounts else 0.0,
            "count": len(amounts)
        }
    return output
