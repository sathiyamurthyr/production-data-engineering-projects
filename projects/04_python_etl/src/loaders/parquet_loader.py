"""
Parquet Loader module for persisting DataFrames in compressed columnar Parquet format.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.loaders.base_loader import BaseLoader, LoadingError
from src.utils.file_utils import ensure_directory


class ParquetLoader(BaseLoader):
    """Loader for persisting data into Apache Parquet files."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Parquet Loader.

        Config Keys:
            path (str): Output file path or directory.
            compression (str): Compression codec ('snappy', 'gzip', 'brotli', 'zstd', default: 'snappy').
            partition_cols (list, optional): Column names for partitioning dataset directory.
        """
        super().__init__(config)
        self.output_path = Path(config.get("path", "output/data.parquet"))
        self.compression = config.get("compression", "snappy")
        self.partition_cols = config.get("partition_cols")

    def load(self, df: pd.DataFrame) -> bool:
        """
        Persist DataFrame to Parquet format.

        Args:
            df: Input DataFrame.

        Returns:
            bool: True on success.

        Raises:
            LoadingError: If pyarrow write fails.
        """
        if df is None:
            raise LoadingError("Cannot load None DataFrame into Parquet.")

        try:
            ensure_directory(self.output_path)
            self.logger.info(
                f"Writing {len(df)} rows to Parquet destination: {self.output_path} (compression='{self.compression}')"
            )

            df_to_save = df.copy()
            # Serialize nested complex types if present
            for col in df_to_save.columns:
                if df_to_save[col].apply(lambda val: isinstance(val, (list, dict))).any():
                    df_to_save[col] = df_to_save[col].astype(str)

            if self.partition_cols:
                valid_parts = [c for c in self.partition_cols if c in df_to_save.columns]
                df_to_save.to_parquet(
                    self.output_path,
                    compression=self.compression,
                    partition_cols=valid_parts,
                    index=False,
                    engine="pyarrow"
                )
            else:
                df_to_save.to_parquet(
                    self.output_path,
                    compression=self.compression,
                    index=False,
                    engine="pyarrow"
                )

            self.logger.info(f"Successfully wrote Parquet file at {self.output_path}")
            return True

        except Exception as e:
            msg = f"Failed writing Parquet artifact at '{self.output_path}': {str(e)}"
            self.logger.error(msg)
            raise LoadingError(msg) from e
