"""
Service Catalog Service
Manages the platform service registry and discovery
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer
import json

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://platform:platform@platform-postgres:5432/platform"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class ServiceModel(Base):
    """Service database model."""
    __tablename__ = "services"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    description = Column(Text)
    version = Column(String)
    owner_team = Column(String, index=True)
    documentation_url = Column(String)
    api_endpoint = Column(String)
    status = Column(String, default="active")
    tags = Column(JSON)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)


class ServiceDependencyModel(Base):
    """Service dependency database model."""
    __tablename__ = "service_dependencies"

    id = Column(String, primary_key=True)
    service_id = Column(String, nullable=False, index=True)
    dependency_id = Column(String, nullable=False, index=True)
    dependency_type = Column(String)  # required, optional, suggested
    created_at = Column(DateTime, default=datetime.utcnow)


class ServiceMetricsModel(Base):
    """Service metrics database model."""
    __tablename__ = "service_metrics"

    id = Column(String, primary_key=True)
    service_id = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    metric_value = Column(String)
    metric_type = Column(String)  # counter, gauge, histogram
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class Service(BaseModel):
    """Service model."""
    id: str
    name: str
    category: str
    description: str
    version: str
    owner_team: str
    documentation_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    status: str = "active"
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    created_by: str


class ServiceDependency(BaseModel):
    """Service dependency model."""
    id: str
    service_id: str
    dependency_id: str
    dependency_type: str


class ServiceMetrics(BaseModel):
    """Service metrics model."""
    id: str
    service_id: str
    metric_name: str
    metric_value: str
    metric_type: str
    recorded_at: datetime


class ServiceCreate(BaseModel):
    """Service creation request."""
    name: str
    category: str
    description: str
    version: str
    owner_team: str
    documentation_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


# ============================================================================
# Service Catalog Service
# ============================================================================

class ServiceCatalogService:
    """Service catalog management service."""

    def __init__(self):
        self.services: Dict[str, Service] = {}
        self.dependencies: Dict[str, List[ServiceDependency]] = {}

    async def initialize(self):
        """Initialize service catalog."""
        logger.info("Initializing service catalog...")

        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Load services from database
        await self._load_services()

        logger.info(f"Service catalog initialized with {len(self.services)} services")

    async def _load_services(self):
        """Load services from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(ServiceModel))
            services = result.scalars().all()

            for svc in services:
                service = Service(
                    id=svc.id,
                    name=svc.name,
                    category=svc.category,
                    description=svc.description,
                    version=svc.version,
                    owner_team=svc.owner_team,
                    documentation_url=svc.documentation_url,
                    api_endpoint=svc.api_endpoint,
                    status=svc.status,
                    tags=svc.tags or [],
                    metadata=svc.metadata or {},
                    created_at=svc.created_at,
                    updated_at=svc.updated_at,
                    created_by=svc.created_by
                )
                self.services[svc.id] = service

    async def health_check(self) -> Dict[str, str]:
        """Health check for service catalog."""
        try:
            # Test database connection
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                await session.execute(select(ServiceModel).limit(1))

            return {
                "status": "healthy",
                "service_count": str(len(self.services)),
                "database": "connected"
            }
        except Exception as e:
            logger.error(f"Service catalog health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def list_services(
        self,
        category: Optional[str] = None,
        team: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Service]:
        """
        List all services with optional filters.
        
        Args:
            category: Filter by category
            team: Filter by owner team
            search: Search in name and description
            
        Returns:
            List of services
        """
        services = list(self.services.values())

        # Apply filters
        if category:
            services = [s for s in services if s.category == category]

        if team:
            services = [s for s in services if s.owner_team == team]

        if search:
            search_lower = search.lower()
            services = [
                s for s in services
                if search_lower in s.name.lower()
                or search_lower in s.description.lower()
            ]

        return services

    async def get_service(self, service_id: str) -> Optional[Service]:
        """
        Get service by ID.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service or None if not found
        """
        return self.services.get(service_id)

    async def create_service(self, request: ServiceCreate) -> Service:
        """
        Create a new service.
        
        Args:
            request: Service creation request
            
        Returns:
            Created service
        """
        import uuid

        service_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create database record
        async with AsyncSessionLocal() as session:
            service_model = ServiceModel(
                id=service_id,
                name=request.name,
                category=request.category,
                description=request.description,
                version=request.version,
                owner_team=request.owner_team,
                documentation_url=request.documentation_url,
                api_endpoint=request.api_endpoint,
                tags=request.tags,
                metadata=request.metadata,
                created_at=now,
                updated_at=now,
                created_by="system"  # TODO: Get from auth context
            )
            session.add(service_model)
            await session.commit()

        # Create service object
        service = Service(
            id=service_id,
            name=request.name,
            category=request.category,
            description=request.description,
            version=request.version,
            owner_team=request.owner_team,
            documentation_url=request.documentation_url,
            api_endpoint=request.api_endpoint,
            tags=request.tags,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
            created_by="system"
        )

        # Add to cache
        self.services[service_id] = service

        logger.info(f"Created service: {service_id} - {request.name}")
        return service

    async def update_service(
        self,
        service_id: str,
        request: ServiceCreate
    ) -> Optional[Service]:
        """
        Update an existing service.
        
        Args:
            service_id: Service identifier
            request: Service update request
            
        Returns:
            Updated service or None if not found
        """
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, update

            # Update database
            stmt = update(ServiceModel).where(ServiceModel.id == service_id).values(
                name=request.name,
                category=request.category,
                description=request.description,
                version=request.version,
                owner_team=request.owner_team,
                documentation_url=request.documentation_url,
                api_endpoint=request.api_endpoint,
                tags=request.tags,
                metadata=request.metadata,
                updated_at=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()

        # Update cache
        service = self.services.get(service_id)
        if service:
            service.name = request.name
            service.category = request.category
            service.description = request.description
            service.version = request.version
            service.owner_team = request.owner_team
            service.documentation_url = request.documentation_url
            service.api_endpoint = request.api_endpoint
            service.tags = request.tags
            service.metadata = request.metadata
            service.updated_at = datetime.utcnow()

            logger.info(f"Updated service: {service_id}")
            return service

        return None

    async def delete_service(self, service_id: str) -> bool:
        """
        Delete a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with AsyncSessionLocal() as session:
            from sqlalchemy import delete

            # Delete from database
            stmt = delete(ServiceModel).where(ServiceModel.id == service_id)
            result = await session.execute(stmt)
            await session.commit()

            deleted = result.rowcount > 0

        # Remove from cache
        if deleted:
            self.services.pop(service_id, None)
            logger.info(f"Deleted service: {service_id}")

        return deleted

    async def get_all_services(self) -> List[Dict[str, Any]]:
        """
        Get all services with summary statistics.
        
        Returns:
            List of service summaries
        """
        services = []

        for service_id, service in self.services.items():
            services.append({
                "id": service.id,
                "name": service.name,
                "category": service.category,
                "owner_team": service.owner_team,
                "status": service.status,
                "version": service.version,
                "tags": service.tags
            })

        return services

    async def get_service_dependencies(
        self,
        service_id: str
    ) -> List[ServiceDependency]:
        """
        Get dependencies for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of dependencies
        """
        return self.dependencies.get(service_id, [])

    async def add_dependency(
        self,
        service_id: str,
        dependency_id: str,
        dependency_type: str = "required"
    ) -> ServiceDependency:
        """
        Add dependency to service.
        
        Args:
            service_id: Service identifier
            dependency_id: Dependency service identifier
            dependency_type: Type of dependency (required, optional, suggested)
            
        Returns:
            Created dependency
        """
        import uuid

        dependency = ServiceDependency(
            id=str(uuid.uuid4()),
            service_id=service_id,
            dependency_id=dependency_id,
            dependency_type=dependency_type
        )

        if service_id not in self.dependencies:
            self.dependencies[service_id] = []

        self.dependencies[service_id].append(dependency)

        logger.info(f"Added dependency: {service_id} -> {dependency_id}")
        return dependency

    async def get_categories(self) -> List[str]:
        """
        Get all service categories.
        
        Returns:
            List of unique categories
        """
        categories = set()
        for service in self.services.values():
            categories.add(service.category)

        return sorted(list(categories))

    async def get_teams(self) -> List[str]:
        """
        Get all owner teams.
        
        Returns:
            List of unique teams
        """
        teams = set()
        for service in self.services.values():
            teams.add(service.owner_team)

        return sorted(list(teams))

    async def record_metrics(
        self,
        service_id: str,
        metric_name: str,
        metric_value: str,
        metric_type: str = "gauge"
    ):
        """
        Record metrics for a service.
        
        Args:
            service_id: Service identifier
            metric_name: Metric name
            metric_value: Metric value
            metric_type: Type of metric (counter, gauge, histogram)
        """
        import uuid

        async with AsyncSessionLocal() as session:
            metric = ServiceMetricsModel(
                id=str(uuid.uuid4()),
                service_id=service_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_type=metric_type
            )
            session.add(metric)
            await session.commit()

        logger.debug(f"Recorded metric: {service_id}.{metric_name} = {metric_value}")