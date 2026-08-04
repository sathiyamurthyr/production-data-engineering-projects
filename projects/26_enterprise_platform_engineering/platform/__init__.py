"""
Enterprise Platform Engineering
Internal Developer Platform (IDP) for Data & AI Teams
"""

import logging
from typing import Dict, Any

__version__ = "1.0.0"
__author__ = "Platform Team"

# Core services
from .auth import AuthenticationService, get_auth_service, auth_service
from .services.service_catalog import ServiceCatalogService
from .services.template_engine import TemplateEngineService
from .services.provisioning import ProvisioningService
from .services.governance import GovernanceService

# Global service instances
service_catalog = ServiceCatalogService()
template_engine = TemplateEngineService()
provisioning_service = ProvisioningService()
governance_service = GovernanceService()


async def initialize_services():
    """Initialize all platform services."""
    logger = logging.getLogger(__name__)
    logger.info("Initializing platform services...")

    # Initialize in dependency order
    await auth_service.initialize()
    await service_catalog.initialize()
    await template_engine.initialize()
    await provisioning_service.initialize()
    await governance_service.initialize()

    logger.info("All platform services initialized successfully")


# Service health check
async def health_check() -> Dict[str, Any]:
    """
    Check health of all services.
    
    Returns:
        Health status of all services
    """
    import logging
    logger = logging.getLogger(__name__)

    services = {}

    try:
        services["auth"] = await auth_service.health_check()
    except Exception as e:
        services["auth"] = {"status": "error", "error": str(e)}

    try:
        services["service_catalog"] = await service_catalog.health_check()
    except Exception as e:
        services["service_catalog"] = {"status": "error", "error": str(e)}

    try:
        services["template_engine"] = await template_engine.health_check()
    except Exception as e:
        services["template_engine"] = {"status": "error", "error": str(e)}

    try:
        services["provisioning"] = await provisioning_service.health_check()
    except Exception as e:
        services["provisioning"] = {"status": "error", "error": str(e)}

    try:
        services["governance"] = await governance_service.health_check()
    except Exception as e:
        services["governance"] = {"status": "error", "error": str(e)}

    # Overall status
    all_healthy = all(s.get("status") == "healthy" for s in services.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": __version__,
        "services": services
    }


__all__ = [
    "AuthenticationService",
    "get_auth_service",
    "auth_service",
    "ServiceCatalogService",
    "service_catalog",
    "TemplateEngineService",
    "template_engine",
    "ProvisioningService",
    "provisioning_service",
    "GovernanceService",
    "governance_service",
    "initialize_services",
    "health_check",
]