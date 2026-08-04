"""
Enterprise Platform Engineering - Platform APIs
Production-ready REST API implementation for Internal Developer Platform
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Import platform components
from platform.services.service_catalog import ServiceCatalogService
from platform.services.template_engine import TemplateEngineService
from platform.services.provisioning import ProvisioningService
from platform.services.governance import GovernanceService
from platform.models.requests import (
    ProvisioningRequest,
    TemplateRequest,
    ServiceRequest,
    ApprovalRequest
)
from platform.models.responses import (
    ProvisioningResponse,
    TemplateResponse,
    ServiceResponse,
    HealthResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Platform services
service_catalog = ServiceCatalogService()
template_engine = TemplateEngineService()
provisioning = ProvisioningService()
governance = GovernanceService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Platform API starting up...")
    await service_catalog.initialize()
    await template_engine.initialize()
    await provisioning.initialize()
    await governance.initialize()
    logger.info("Platform API ready")
    yield
    # Shutdown
    logger.info("Platform API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Enterprise Platform Engineering API",
    description="Internal Developer Platform (IDP) REST API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# Health & Status
# ============================================================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Platform health check endpoint.
    Returns the health status of all platform services.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "service_catalog": await service_catalog.health_check(),
            "template_engine": await template_engine.health_check(),
            "provisioning": await provisioning.health_check(),
            "governance": await governance.health_check()
        }
    }

    # Check if all services are healthy
    all_healthy = all(
        service["status"] == "healthy"
        for service in health_status["services"].values()
    )

    if not all_healthy:
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/v1/status", tags=["Health"])
async def platform_status():
    """
    Detailed platform status.
    """
    return {
        "platform": {
            "name": "Enterprise Platform Engineering",
            "version": "1.0.0",
            "environment": "production",
            "uptime": "14d 6h 23m"
        },
        "services": await service_catalog.get_all_services(),
        "statistics": {
            "total_provisions": 1234,
            "active_workspaces": 456,
            "templates_available": 25,
            "developers_active": 789
        }
    }


# ============================================================================
# Authentication
# ============================================================================

@app.post("/api/v1/auth/token", tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login.
    Returns access token for authenticated requests.
    """
    from platform.auth import authenticate_user, create_access_token

    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=timedelta(minutes=30)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800
    }


@app.get("/api/v1/auth/me", tags=["Authentication"])
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current user information.
    """
    from platform.auth import get_current_user_from_token

    user = await get_current_user_from_token(token)
    return {
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "teams": user.teams,
        "permissions": user.permissions
    }


# ============================================================================
# Service Catalog
# ============================================================================

@app.get("/api/v1/services", response_model=List[ServiceResponse], tags=["Service Catalog"])
async def list_services(
    category: Optional[str] = None,
    team: Optional[str] = None,
    search: Optional[str] = None,
    token: str = Depends(oauth2_scheme)
):
    """
    List all available platform services.
    Optional filters: category, team, search query.
    """
    services = await service_catalog.list_services(
        category=category,
        team=team,
        search=search
    )
    return services


@app.get("/api/v1/services/{service_id}", response_model=ServiceResponse, tags=["Service Catalog"])
async def get_service(service_id: str, token: str = Depends(oauth2_scheme)):
    """
    Get detailed information about a specific service.
    """
    service = await service_catalog.get_service(service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
    return service


@app.post("/api/v1/services", response_model=ServiceResponse, tags=["Service Catalog"])
async def create_service(
    request: ServiceRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Register a new service in the catalog.
    """
    from platform.auth import require_permission

    await require_permission(token, "services:write")

    service = await service_catalog.create_service(request)
    return service


@app.put("/api/v1/services/{service_id}", response_model=ServiceResponse, tags=["Service Catalog"])
async def update_service(
    service_id: str,
    request: ServiceRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Update an existing service.
    """
    from platform.auth import require_permission

    await require_permission(token, "services:write")

    service = await service_catalog.update_service(service_id, request)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
    return service


@app.delete("/api/v1/services/{service_id}", tags=["Service Catalog"])
async def delete_service(service_id: str, token: str = Depends(oauth2_scheme)):
    """
    Delete a service from the catalog.
    """
    from platform.auth import require_permission

    await require_permission(token, "services:admin")

    success = await service_catalog.delete_service(service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
    return {"message": f"Service {service_id} deleted successfully"}


# ============================================================================
# Templates
# ============================================================================

@app.get("/api/v1/templates", response_model=List[TemplateResponse], tags=["Templates"])
async def list_templates(
    category: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    token: str = Depends(oauth2_scheme)
):
    """
    List available golden path templates.
    """
    templates = await template_engine.list_templates(
        category=category,
        tags=tags
    )
    return templates


@app.get("/api/v1/templates/{template_id}", response_model=TemplateResponse, tags=["Templates"])
async def get_template(template_id: str, token: str = Depends(oauth2_scheme)):
    """
    Get detailed information about a template.
    """
    template = await template_engine.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    return template


@app.post("/api/v1/templates/render", tags=["Templates"])
async def render_template(
    request: TemplateRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Render a template with provided variables.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    # Validate template exists
    template = await template_engine.get_template(request.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {request.template_id} not found"
        )

    # Validate variables against schema
    validation_result = await template_engine.validate_variables(
        request.template_id,
        request.variables
    )

    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Invalid template variables",
                "errors": validation_result.errors
            }
        )

    # Check governance policies
    policy_result = await governance.evaluate_template(request)
    if not policy_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Template violates governance policies",
                "violations": policy_result.violations
            }
        )

    # Render template
    rendered = await template_engine.render(
        request.template_id,
        request.variables,
        user=user
    )

    return {
        "template_id": request.template_id,
        "variables": request.variables,
        "rendered_content": rendered.content,
        "files": rendered.files
    }


@app.post("/api/v1/templates", response_model=TemplateResponse, tags=["Templates"])
async def create_template(
    request: TemplateRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Create a new template.
    """
    from platform.auth import require_permission

    await require_permission(token, "templates:write")

    template = await template_engine.create_template(request)
    return template


# ============================================================================
# Provisioning
# ============================================================================

@app.post("/api/v1/provision", response_model=ProvisioningResponse, tags=["Provisioning"])
async def provision_resource(
    request: ProvisioningRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Provision a new resource from a template.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    # Validate request
    validation_result = await provisioning.validate_request(request)
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Invalid provisioning request",
                "errors": validation_result.errors
            }
        )

    # Check governance policies
    policy_result = await governance.evaluate_provisioning(request, user)
    if not policy_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Provisioning request violates policies",
                "violations": policy_result.violations
            }
        )

    # Check if approval is required
    if policy_result.requires_approval:
        approval = await provisioning.create_approval_request(request, user)
        return ProvisioningResponse(
            provisioning_id=None,
            status="pending_approval",
            approval_id=approval.id,
            message="Approval required before provisioning",
            estimated_time=None,
            created_at=datetime.utcnow().isoformat()
        )

    # Provision resource
    provisioning_result = await provisioning.provision(request, user)

    return ProvisioningResponse(
        provisioning_id=provisioning_result.id,
        status=provisioning_result.status,
        message=f"Resource provisioning started",
        estimated_time=provisioning_result.estimated_time,
        created_at=datetime.utcnow().isoformat()
    )


@app.get("/api/v1/provision/{provisioning_id}", response_model=ProvisioningResponse, tags=["Provisioning"])
async def get_provisioning_status(
    provisioning_id: str,
    token: str = Depends(oauth2_scheme)
):
    """
    Get the status of a provisioning request.
    """
    status = await provisioning.get_status(provisioning_id)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provisioning request {provisioning_id} not found"
        )
    return status


@app.get("/api/v1/provision", response_model=List[ProvisioningResponse], tags=["Provisioning"])
async def list_provisioning_requests(
    status: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    token: str = Depends(oauth2_scheme)
):
    """
    List provisioning requests with optional filters.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    requests = await provisioning.list_requests(
        user=user,
        status=status,
        team=team,
        limit=limit,
        offset=offset
    )
    return requests


@app.post("/api/v1/provision/{provisioning_id}/cancel", tags=["Provisioning"])
async def cancel_provisioning(
    provisioning_id: str,
    token: str = Depends(oauth2_scheme)
):
    """
    Cancel a provisioning request.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    result = await provisioning.cancel(provisioning_id, user)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provisioning request {provisioning_id} not found"
        )
    return {"message": f"Provisioning request {provisioning_id} cancelled"}


# ============================================================================
# Approvals
# ============================================================================

@app.get("/api/v1/approvals/pending", tags=["Approvals"])
async def list_pending_approvals(token: str = Depends(oauth2_scheme)):
    """
    List pending approval requests for the current user.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    approvals = await provisioning.list_pending_approvals(user)
    return approvals


@app.post("/api/v1/approvals/{approval_id}/approve", tags=["Approvals"])
async def approve_request(
    approval_id: str,
    request: ApprovalRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Approve a provisioning request.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    result = await provisioning.approve(approval_id, user, request.comment)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found"
        )

    return {"message": f"Approval {approval_id} approved"}


@app.post("/api/v1/approvals/{approval_id}/reject", tags=["Approvals"])
async def reject_request(
    approval_id: str,
    request: ApprovalRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Reject a provisioning request.
    """
    from platform.auth import get_current_user_from_token
    user = await get_current_user_from_token(token)

    result = await provisioning.reject(approval_id, user, request.comment)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found"
        )

    return {"message": f"Approval {approval_id} rejected"}


# ============================================================================
# Governance
# ============================================================================

@app.get("/api/v1/policies", tags=["Governance"])
async def list_policies(token: str = Depends(oauth2_scheme)):
    """
    List all governance policies.
    """
    from platform.auth import require_permission
    await require_permission(token, "policies:read")

    policies = await governance.list_policies()
    return policies


@app.get("/api/v1/policies/{policy_id}", tags=["Governance"])
async def get_policy(policy_id: str, token: str = Depends(oauth2_scheme)):
    """
    Get detailed information about a policy.
    """
    from platform.auth import require_permission
    await require_permission(token, "policies:read")

    policy = await governance.get_policy(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )
    return policy


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)