"""
Shared Identity Services for Enterprise Multi-Cloud Data Platform

This module provides unified identity and access management across Azure and AWS.
"""

from .identity_federation import IdentityFederationService
from .role_mapper import CrossCloudRoleMapper
from .sso_provider import SSOProvider
from .access_governance import AccessGovernanceService

__all__ = [
    "IdentityFederationService",
    "CrossCloudRoleMapper",
    "SSOProvider",
    "AccessGovernanceService",
]