"""
Abstract base class definition for all data loaders in the framework.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger("etl_pipeline.loaders")


class LoadingError(Exception):
    """Custom exception raised when data load operations fail."""
    pass


class BaseLoader(ABC):
    """Abstract Base Class for Data Loaders."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the loader with target destination configuration.

        Args:
            config: Destination target configuration settings.
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def load(self, df: pd.DataFrame) -> bool:
        """
        Load DataFrame into target destination.

        Args:
            df: Transformed dataset to write.

        Returns:
            bool: True if loading completed successfully.

        Raises:
            LoadingError: If load operation fails.
        """
        pass
