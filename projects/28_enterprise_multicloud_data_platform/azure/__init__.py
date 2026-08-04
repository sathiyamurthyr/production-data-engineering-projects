"""
Azure Integration Services for Enterprise Multi-Cloud Data Platform

This module provides Azure-specific integrations.
"""

from .storage_service import AzureStorageService
from .compute_service import AzureComputeService
from .data_services import AzureDataServices
from .monitoring_service import AzureMonitoringService

__all__ = [
    "AzureStorageService",
    "AzureComputeService",
    "AzureDataServices",
    "AzureMonitoringService",
]