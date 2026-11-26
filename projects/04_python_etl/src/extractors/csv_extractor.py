"""
CSV Extractor module for reading delimited flat files.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Generator
import pandas as pd

from src.extractors.base_extractor import BaseExtractor, ExtractionError


class CSVExtractor(BaseExtractor):
    """Extractor for comma and tab separated values files."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CSV Extractor.

        Config Keys:
            path (str): File path to CSV file.
            delimiter (str): Delimiter character (default: ',').
            encoding (str): Encoding type (default: 'utf-8').
            chunk_size (int, optional): Number of rows per chunk if streaming.
        """
        super().__init__(config)
        self.file_path = Path(config.get("path", ""))
        self.delimiter = config.get("delimiter", ",")
        self.encoding = config.get("encoding", "utf-8")
        self.chunk_size = config.get("chunk_size")

    def extract(self) -> pd.DataFrame:
        """
        Extract full dataset into a single pandas DataFrame.

        Returns:
            pd.DataFrame: Extracted tabular data.

        Raises:
            ExtractionError: If file is missing or unparseable.
        """
        if not self.file_path.exists():
            msg = f"CSV file not found at path: {self.file_path}"
            self.logger.error(msg)
            raise ExtractionError(msg)

        try:
            self.logger.info(f"Extracting CSV file from {self.file_path}")
            df = pd.read_csv(
                self.file_path,
                delimiter=self.delimiter,
                encoding=self.encoding,
                on_bad_lines="skip",
            )
            self.logger.info(f"Successfully extracted {len(df)} records from {self.file_path.name}")
            return df
        except Exception as e:
            msg = f"Failed to extract CSV file {self.file_path}: {str(e)}"
            self.logger.error(msg)
            raise ExtractionError(msg) from e

    def extract_chunks(self) -> Generator[pd.DataFrame, None, None]:
        """
        Stream extraction in chunks to manage memory footprint for large files.

        Yields:
            pd.DataFrame: Chunk DataFrame.

        Raises:
            ExtractionError: If file stream breaks.
        """
        if not self.file_path.exists():
            raise ExtractionError(f"CSV file not found: {self.file_path}")

        chunk_size = self.chunk_size or 1000
        try:
            self.logger.info(f"Streaming CSV chunks (size={chunk_size}) from {self.file_path}")
            chunk_reader = pd.read_csv(
                self.file_path,
                delimiter=self.delimiter,
                encoding=self.encoding,
                chunksize=chunk_size,
            )
            for i, chunk in enumerate(chunk_reader):
                self.logger.debug(f"Yielding chunk {i+1} with {len(chunk)} rows")
                yield chunk
        except Exception as e:
            msg = f"Error during CSV chunk extraction from {self.file_path}: {str(e)}"
            self.logger.error(msg)
            raise ExtractionError(msg) from e
