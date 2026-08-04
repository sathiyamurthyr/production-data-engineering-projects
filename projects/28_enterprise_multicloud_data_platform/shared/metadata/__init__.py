"""
Shared Metadata Services for Enterprise Multi-Cloud Data Platform

This module provides unified metadata management across Azure and AWS.
"""

from .metadata_catalog import MetadataCatalog
from .data_lineage import DataLineageTracker
from .schema_registry import SchemaRegistry
from .discovery_service import DiscoveryService

__all__ = [
    "MetadataCatalog",
    "DataLineageTracker",
    "SchemaRegistry",
    "DiscoveryService",
]