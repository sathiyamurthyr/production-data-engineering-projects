"""
CSV Loader module for persisting DataFrames to flat files.
"""

from pathlib import Path
from typing import Any, Dict
import pandas as pd

from src.loaders.base_loader import BaseLoader, LoadingError
from src.utils.file_utils import ensure_directory


class CSVLoader(BaseLoader):
    """Loader for persisting data into CSV files."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CSV Loader.

        Config Keys:
            path (str): Output destination path.
            index (bool): Whether to include DataFrame index (default: False).
            mode (str): File write mode ('w' or 'a', default: 'w').
        """
        super().__init__(config)
        self.output_path = Path(config.get("path", "output/data.csv"))
        self.index = config.get("index", False)
        self.mode = config.get("mode", "w")

    def load(self, df: pd.DataFrame) -> bool:
        """
        Persist DataFrame to target CSV path.

        Args:
            df: Input DataFrame to export.

        Returns:
            bool: True on success.

        Raises:
            LoadingError: If directory creation or write operation fails.
        """
        if df is None:
            raise LoadingError("Cannot load None DataFrame into CSV.")

        try:
            ensure_directory(self.output_path)
            self.logger.info(f"Writing {len(df)} records to CSV destination: {self.output_path}")

            # Convert non-serializable objects (like list/dict columns) to JSON strings
            df_to_save = df.copy()
            for col in df_to_save.columns:
                if df_to_save[col].apply(lambda val: isinstance(val, (list, dict))).any():
                    df_to_save[col] = df_to_save[col].astype(str)

            df_to_save.to_csv(
                self.output_path,
                index=self.index,
                mode=self.mode,
                encoding="utf-8"
            )
            self.logger.info(f"Successfully saved CSV artifact at {self.output_path}")
            return True

        except Exception as e:
            msg = f"Failed writing DataFrame to CSV file '{self.output_path}': {str(e)}"
            self.logger.error(msg)
            raise LoadingError(msg) from e
