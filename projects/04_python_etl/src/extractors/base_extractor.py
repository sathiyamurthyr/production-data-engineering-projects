"""
Abstract base class definition for all data extractors in the framework.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger("etl_pipeline.extractors")


class ExtractionError(Exception):
    """Custom exception raised when data extraction fails."""
    pass


class BaseExtractor(ABC):
    """Abstract Base Class for Data Extractors."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the extractor with component-specific configuration.

        Args:
            config: Configuration dictionary containing source connection details or file paths.
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """
        Extract data from the target source and return a pandas DataFrame.

        Returns:
            pd.DataFrame: Extracted dataset.

        Raises:
            ExtractionError: If extraction fails.
        """
        pass
