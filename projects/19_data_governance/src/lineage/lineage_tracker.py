"""
Lineage Tracker Module
======================
Captures operational, column-level, and table-level data lineage dependencies
across data pipelines and transformations.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class LineageEdge:
    """Represents a directional dependency link between source and target data assets."""
    source_asset: str  # e.g., "raw_customers"
    target_asset: str  # e.g., "cleaned_customers"
    transformation_type: str = "ETL_PIPELINE"  # "COPY", "JOIN", "AGGREGATION", "FILTER"
    source_column: Optional[str] = None
    target_column: Optional[str] = None
    pipeline_name: str = "default_pipeline"
    execution_id: str = "exec_001"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge object to dictionary."""
        return asdict(self)


class LineageTracker:
    """
    Tracks and records data flow operations between datasets and columns.
    """

    def __init__(self) -> None:
        self._edges: List[LineageEdge] = []

    def record_lineage(
        self,
        source_asset: str,
        target_asset: str,
        transformation_type: str = "ETL_PIPELINE",
        source_column: Optional[str] = None,
        target_column: Optional[str] = None,
        pipeline_name: str = "default_pipeline",
        execution_id: str = "exec_001",
    ) -> LineageEdge:
        """
        Record a lineage link from source asset/column to target asset/column.
        
        Args:
            source_asset: Source table/dataset ID.
            target_asset: Target table/dataset ID.
            transformation_type: Type of transformation operation.
            source_column: Optional column name in source.
            target_column: Optional column name in target.
            pipeline_name: Pipeline or DAG name.
            execution_id: Job run execution ID.
            
        Returns:
            Recorded LineageEdge object.
        """
        edge = LineageEdge(
            source_asset=source_asset,
            target_asset=target_asset,
            transformation_type=transformation_type,
            source_column=source_column,
            target_column=target_column,
            pipeline_name=pipeline_name,
            execution_id=execution_id,
        )
        self._edges.append(edge)
        logger.info(
            f"Lineage recorded: {source_asset}"
            f"{'.' + source_column if source_column else ''} -> "
            f"{target_asset}"
            f"{'.' + target_column if target_column else ''} via [{transformation_type}]."
        )
        return edge

    def get_all_edges(self) -> List[LineageEdge]:
        """Return all recorded lineage edges."""
        return list(self._edges)

    def get_downstream_edges(self, asset_name: str) -> List[LineageEdge]:
        """Find all direct downstream lineage edges where asset_name is the source."""
        return [e for e in self._edges if e.source_asset == asset_name]

    def get_upstream_edges(self, asset_name: str) -> List[LineageEdge]:
        """Find all direct upstream lineage edges where asset_name is the target."""
        return [e for e in self._edges if e.target_asset == asset_name]
