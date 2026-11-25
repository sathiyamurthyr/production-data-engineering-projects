"""
Extractor module index exporting extraction classes.
"""

from src.extractors.base_extractor import BaseExtractor, ExtractionError
from src.extractors.csv_extractor import CSVExtractor
from src.extractors.api_extractor import APIExtractor
from src.extractors.database_extractor import DatabaseExtractor
from src.extractors.json_extractor import JSONExtractor

__all__ = [
    "BaseExtractor",
    "ExtractionError",
    "CSVExtractor",
    "APIExtractor",
    "DatabaseExtractor",
    "JSONExtractor",
]
