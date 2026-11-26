"""
Abstract base class definition for data transformers in the ETL framework.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger("etl_pipeline.transformers")


class TransformationError(Exception):
    """Custom exception raised during transformation operations."""
    pass


class BaseTransformer(ABC):
    """Abstract Base Class for Data Transformers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the transformer with component configuration.

        Args:
            config: Transformer configuration parameters.
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the input pandas DataFrame and return transformed result.

        Args:
            df: Input DataFrame.

        Returns:
            pd.DataFrame: Transformed DataFrame.

        Raises:
            TransformationError: If transformation fails.
        """
        pass
