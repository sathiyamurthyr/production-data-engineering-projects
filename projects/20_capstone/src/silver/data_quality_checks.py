import logging
from typing import List, Dict, Any
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DataQualityChecker:
    """Enterprise-grade Data Quality check engine supporting both PySpark and Pandas/DuckDB environments."""

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.dq_cfg = self.config.data_quality_config

    def run_null_check(self, df, columns: List[str]) -> Dict[str, Any]:
        """Checks if specified columns have null values."""
        results = {"pass": True, "failed_columns": [], "null_counts": {}}
        
        # Check if Spark DataFrame
        if hasattr(df, "sparkSession"):
            from pyspark.sql.functions import col, count, when
            null_exprs = [count(when(col(c).isNull(), c)).alias(c) for c in columns]
            null_counts_row = df.select(*null_exprs).collect()[0]
            for col_name in columns:
                cnt = null_counts_row[col_name]
                if cnt > 0:
                    results["pass"] = False
                    results["failed_columns"].append(col_name)
                    results["null_counts"][col_name] = cnt
        else:
            # Pandas fallback
            for col_name in columns:
                cnt = int(df[col_name].isnull().sum())
                if cnt > 0:
                    results["pass"] = False
                    results["failed_columns"].append(col_name)
                    results["null_counts"][col_name] = cnt
                    
        return results

    def run_range_check(self, df, col_name: str, min_val: float, max_val: float) -> Dict[str, Any]:
        """Validates that a numeric column's values lie strictly between min_val and max_val."""
        results = {"pass": True, "out_of_range_count": 0}
        
        if hasattr(df, "sparkSession"):
            from pyspark.sql.functions import col
            out_of_range = df.filter((col(col_name) < min_val) | (col(col_name) > max_val))
            cnt = out_of_range.count()
            if cnt > 0:
                results["pass"] = False
                results["out_of_range_count"] = cnt
        else:
            # Pandas fallback
            cnt = int(((df[col_name] < min_val) | (df[col_name] > max_val)).sum())
            if cnt > 0:
                results["pass"] = False
                results["out_of_range_count"] = cnt
                
        return results

    def run_uniqueness_check(self, df, pk_cols: List[str]) -> Dict[str, Any]:
        """Verifies that a list of primary key columns uniquely identifies each row."""
        results = {"pass": True, "total_records": 0, "unique_records": 0}
        
        if hasattr(df, "sparkSession"):
            results["total_records"] = df.count()
            results["unique_records"] = df.select(*pk_cols).distinct().count()
            if results["total_records"] != results["unique_records"]:
                results["pass"] = False
        else:
            # Pandas fallback
            results["total_records"] = len(df)
            results["unique_records"] = len(df.drop_duplicates(subset=pk_cols))
            if results["total_records"] != results["unique_records"]:
                results["pass"] = False
                
        return results

    def run_referential_integrity(self, df_child, child_key: str, df_parent, parent_key: str) -> Dict[str, Any]:
        """Ensures that every key in the child dataset exists in the parent dataset."""
        results = {"pass": True, "missing_keys_count": 0}
        
        if hasattr(df_child, "sparkSession") and hasattr(df_parent, "sparkSession"):
            child_keys = df_child.select(child_key).distinct()
            parent_keys = df_parent.select(parent_key).distinct()
            missing = child_keys.join(parent_keys, child_keys[child_key] == parent_keys[parent_key], "leftanti")
            cnt = missing.count()
            if cnt > 0:
                results["pass"] = False
                results["missing_keys_count"] = cnt
        else:
            # Pandas fallback
            child_set = set(df_child[child_key].dropna())
            parent_set = set(df_parent[parent_key].dropna())
            missing = child_set - parent_set
            if len(missing) > 0:
                results["pass"] = False
                # Calculate number of child rows with missing keys
                results["missing_keys_count"] = int(df_child[df_child[child_key].isin(missing)].shape[0])
                
        return results
