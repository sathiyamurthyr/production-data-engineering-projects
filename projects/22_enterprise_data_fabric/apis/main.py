"""Data Fabric REST API - FastAPI-based metadata API."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from platform.metadata.models import Asset, AssetType, SensitivityLevel, Column
from platform.catalog.catalog import CatalogService
from platform.search.search import SearchService
from platform.lineage.tracker import LineageTracker
from platform.policies.engine import PolicyEngine
from platform.knowledge_graph.graph import KnowledgeGraph
from platform.discovery.discovery import DataDiscoveryService


# Request/Response Models
class AssetCreate(BaseModel):
    """Asset creation request."""
    name: str
    description: str | None = None
    asset_type: str
    platform: str
    platform_id: str
    domain: str | None = None
    owner: str | None = None
    tags: list[str] = []
    sensitivity: str = "internal"
    metadata: dict[str, Any] = {}


class AssetUpdate(BaseModel):
    """Asset update request."""
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    sensitivity: str | None = None
    metadata: dict[str, Any] | None = None


class LineageResponse(BaseModel):
    """Lineage response."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SearchResponse(BaseModel):
    """Search response."""
    results: list[dict[str, Any]]
    total: int
    facets: dict[str, Any]


class PolicyViolationResponse(BaseModel):
    """Policy violation response."""
    policy_id: str
    asset_id: str
    rule_condition: str
    action_taken: str
    resolved: bool = False


class DiscoveryReportResponse(BaseModel):
    """Discovery report response."""
    total_assets: int
    sensitive_assets: int
    pii_assets: int
    phi_assets: int
    orphaned_assets: int
    duplicate_assets: int
    data_products: int
    recommendations: list[dict[str, Any]]


def create_app(
    catalog: CatalogService,
    search: SearchService,
    lineage: LineageTracker,
    policy_engine: PolicyEngine,
    knowledge_graph: KnowledgeGraph,
    discovery: DataDiscoveryService,
) -> FastAPI:
    """Create FastAPI application with all routes."""
    app = FastAPI(
        title="Enterprise Data Fabric API",
        description="Intelligent metadata management and data governance platform",
        version="1.0.0",
    )

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "data-fabric"}

    # Asset endpoints
    @app.post("/api/v1/assets", response_model=Asset)
    async def create_asset(asset_create: AssetCreate) -> Asset:
        """Create a new asset."""
        asset = Asset(
            name=asset_create.name,
            description=asset_create.description,
            asset_type=AssetType(asset_create.asset_type),
            platform=asset_create.platform,
            platform_id=asset_create.platform_id,
            domain=asset_create.domain,
            owner=asset_create.owner,
            tags=asset_create.tags,
            sensitivity=SensitivityLevel(asset_create.sensitivity),
            metadata=asset_create.metadata,
        )
        return catalog.register_asset(asset)

    @app.get("/api/v1/assets", response_model=list[Asset])
    async def list_assets(
        platform: str | None = None,
        domain: str | None = None,
        asset_type: str | None = None,
        sensitivity: str | None = None,
        owner: str | None = None,
        limit: int = Query(default=100, le=1000),
        offset: int = 0,
    ) -> list[Asset]:
        """List assets with optional filters."""
        return catalog.list_assets(
            platform=platform,
            domain=domain,
            asset_type=AssetType(asset_type) if asset_type else None,
            sensitivity=SensitivityLevel(sensitivity) if sensitivity else None,
            owner=owner,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/v1/assets/{urn}", response_model=Asset)
    async def get_asset(urn: str) -> Asset:
        """Get asset by URN."""
        asset = catalog.get_asset(urn)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset

    @app.put("/api/v1/assets/{urn}", response_model=Asset)
    async def update_asset(urn: str, asset_update: AssetUpdate) -> Asset:
        """Update asset metadata."""
        updates = asset_update.model_dump(exclude_none=True)
        asset = catalog.update_asset(urn, updates)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset

    @app.delete("/api/v1/assets/{urn}")
    async def delete_asset(urn: str) -> dict[str, str]:
        """Delete asset from catalog."""
        success = catalog.delete_asset(urn)
        if not success:
            raise HTTPException(status_code=404, detail="Asset not found")
        return {"message": "Asset deleted successfully"}

    # Lineage endpoints
    @app.get("/api/v1/assets/{urn}/lineage", response_model=LineageResponse)
    async def get_asset_lineage(urn: str, depth: int = 3) -> LineageResponse:
        """Get lineage for an asset."""
        lineage_data = catalog.get_asset_lineage(urn, depth)
        return LineageResponse(**lineage_data)

    @app.get("/api/v1/assets/{urn}/dependencies")
    async def get_asset_dependencies(urn: str) -> dict[str, list[str]]:
        """Get asset dependencies."""
        return catalog.get_asset_dependencies(urn)

    # Search endpoints
    @app.get("/api/v1/search", response_model=SearchResponse)
    async def search_assets(
        q: str,
        limit: int = Query(default=50, le=100),
    ) -> SearchResponse:
        """Search for assets."""
        results = search.search(q, limit=limit)
        return SearchResponse(
            results=[r["asset"].model_dump() for r in results],
            total=len(results),
            facets={},
        )

    @app.get("/api/v1/search/suggestions")
    async def get_search_suggestions(prefix: str, limit: int = 10) -> list[str]:
        """Get search suggestions."""
        return search.get_suggestions(prefix, limit)

    # Policy endpoints
    @app.post("/api/v1/policies/validate")
    async def validate_asset_policies(asset: Asset) -> list[PolicyViolationResponse]:
        """Validate asset against all policies."""
        violations = policy_engine.evaluate_asset(asset.model_dump())
        return [
            PolicyViolationResponse(
                policy_id=v.policy_id,
                asset_id=v.asset_id,
                rule_condition=v.rule_condition,
                action_taken=v.action_taken,
                resolved=v.resolved,
            )
            for v in violations
        ]

    @app.get("/api/v1/policies/report")
    async def get_policy_report() -> dict[str, Any]:
        """Get policy compliance report."""
        return policy_engine.get_policy_report()

    # Discovery endpoints
    @app.get("/api/v1/discovery/report", response_model=DiscoveryReportResponse)
    async def get_discovery_report() -> DiscoveryReportResponse:
        """Get discovery report."""
        report = discovery.get_discovery_report()
        return DiscoveryReportResponse(**report)

    @app.get("/api/v1/discovery/sensitive")
    async def discover_sensitive_assets() -> list[dict[str, Any]]:
        """Discover sensitive assets."""
        assets = catalog.list_assets(limit=1000)
        sensitive = []
        for asset in assets:
            findings = discovery.discover_sensitive_data(asset)
            if findings["pii"] or findings["phi"] or findings["financial"]:
                sensitive.append({
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "findings": findings,
                })
        return sensitive

    # Catalog statistics
    @app.get("/api/v1/stats")
    async def get_catalog_stats() -> dict[str, Any]:
        """Get catalog statistics."""
        return catalog.get_catalog_stats()

    # Knowledge graph endpoints
    @app.get("/api/v1/graph/neighbors/{node_id}")
    async def get_node_neighbors(node_id: str, depth: int = 2) -> dict[str, Any]:
        """Get neighbors of a node in knowledge graph."""
        # Implementation would query Neo4j
        return {"nodes": [], "edges": []}

    return app