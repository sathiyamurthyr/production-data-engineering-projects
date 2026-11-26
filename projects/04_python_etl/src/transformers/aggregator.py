"""
Aggregator transformer for calculating summary metrics, KPI rollups,
and group-by aggregations.
"""

from typing import Any, Dict, List, Optional
import pandas as pd

from src.transformers.base_transformer import BaseTransformer, TransformationError


class DataAggregator(BaseTransformer):
    """Transformer for aggregations, metrics calculation, and analytical rollups."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Data Aggregator.

        Config Keys:
            group_by_columns (list): List of column names to group by.
            aggregations (dict): Mapping of source columns to aggregation metrics (e.g. {'grand_total': ['sum', 'mean']}).
        """
        super().__init__(config)
        self.group_by_columns = config.get("group_by_columns", ["country"])
        self.aggregations = config.get(
            "aggregations",
            {"total_spent": ["sum", "mean", "count"]}
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate input DataFrame based on configured groupings and metrics.

        Args:
            df: Input DataFrame.

        Returns:
            pd.DataFrame: Aggregated summary DataFrame.

        Raises:
            TransformationError: If group by or aggregation fails.
        """
        if df.empty:
            self.logger.warning("DataAggregator received empty DataFrame.")
            return df.copy()

        # Check if group by columns exist
        missing_group_cols = [col for col in self.group_by_columns if col not in df.columns]
        if missing_group_cols:
            msg = f"Cannot group by missing columns: {missing_group_cols}"
            self.logger.error(msg)
            raise TransformationError(msg)

        try:
            self.logger.info(f"Grouping DataFrame by {self.group_by_columns}")
            
            # Filter aggregations dict to available columns in df
            valid_aggs = {
                col: funcs for col, funcs in self.aggregations.items() if col in df.columns
            }

            if not valid_aggs:
                self.logger.warning("No aggregation target columns found in DataFrame. Performing record count.")
                agg_df = df.groupby(self.group_by_columns).size().reset_index(name="record_count")
            else:
                agg_df = df.groupby(self.group_by_columns).agg(valid_aggs).reset_index()
                # Flatten multi-index column headers if created
                if isinstance(agg_df.columns, pd.MultiIndex):
                    agg_df.columns = [
                        f"{col[0]}_{col[1]}" if col[1] else col[0]
                        for col in agg_df.columns
                    ]

            self.logger.info(f"Aggregation completed. Result shape: {agg_df.shape}")
            return agg_df

        except Exception as e:
            msg = f"Aggregation operation failed: {str(e)}"
            self.logger.error(msg)
            raise TransformationError(msg) from e
