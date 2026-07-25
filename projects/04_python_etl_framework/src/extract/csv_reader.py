"""
CSV Extractor for ETL Pipeline

Reads data from CSV files with configurable options.
"""

from pathlib import Path
from typing import Any
import csv

from pydantic import BaseModel, Field


class CSVConfig(BaseModel):
    """Configuration for CSV extraction."""
    path: str
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True
    chunk_size: int = 10000


class CSVReader:
    """
    Production CSV extractor with chunking and encoding support.
    """
    
    def __init__(self, config: CSVConfig | dict[str, Any] | None = None, **kwargs):
        """Initialize CSV reader with configuration."""
        if config is None:
            config = CSVConfig(**kwargs)
        elif isinstance(config, dict):
            config = CSVConfig(**config)
        self.config = config
    
    def extract(self) -> list[dict[str, Any]]:
        """Extract all records from CSV file."""
        path = Path(self.config.path)
        records = []
        
        with open(path, "r", encoding=self.config.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=self.config.delimiter)
            
            for row in reader:
                # Convert empty strings to None
                clean_row = {
                    k: (v if v != "" else None)
                    for k, v in row.items()
                }
                records.append(clean_row)
        
        return records
    
    def extract_chunks(self) -> list[list[dict[str, Any]]]:
        """Extract records in chunks for memory efficiency."""
        path = Path(self.config.path)
        chunks = []
        current_chunk = []
        
        with open(path, "r", encoding=self.config.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=self.config.delimiter)
            
            for row in reader:
                clean_row = {k: (v if v != "" else None) for k, v in row.items()}
                current_chunk.append(clean_row)
                
                if len(current_chunk) >= self.config.chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks