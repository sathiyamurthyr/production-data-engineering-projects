"""
================================================================================
MODULE 24: Object-Oriented Programming (OOP) for Data Pipelines
================================================================================
1. EXPLANATION:
OOP encapsulates state and behavior. Base classes define Extractor, Transformer, and Loader contracts.

2. BUSINESS USE CASE:
Create an abstract DataConnector class and CSVDataConnector implementation.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any

class BaseConnector(ABC):
    """Abstract Base Class for Data Pipeline Connectors."""
    
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def read_data((self) -> List[Dict[str, Any]]:
        pass

class FileConnector(BaseConnector):
    """Concrete File Connector implementation."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def connect(self) -> bool:
        return self.file_path.exists()

    def read_data(self) -> List[Dict[str, Any]]:
        return [{"status": "connected", "path": str(self.file_path)}]
