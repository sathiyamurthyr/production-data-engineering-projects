"""
Unified Metadata Catalog for Cross-Cloud Data Management

This module provides a unified metadata catalog across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types"""
    DATABASE = "database"
    TABLE = "table"
    VIEW = "view"
    PIPELINE = "pipeline"
    TOPIC = "topic"
    STORAGE = "storage"
    FUNCTION = "function"
    MODEL = "model"
    FEATURE = "feature"
    NOTEBOOK = "notebook"


class MetadataStatus(str, Enum):
    """Metadata status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DRAFT = "draft"


class DataClassification(BaseModel):
    """Data classification"""
    sensitivity: str  # public, internal, confidential, restricted
    pii: bool = False
    phi: bool = False
    pci: bool = False
    retention_period_days: int = 365
    encryption_required: bool = True


class MetadataEntry(BaseModel):
    """Metadata entry"""
    resource_id: str
    resource_type: ResourceType
    name: str
    description: str
    cloud: CloudProvider
    region: str
    owner: str
    status: MetadataStatus
    classification: DataClassification
    schema: Optional[Dict[str, Any]] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None


class MetadataCatalog:
    """
    Unified metadata catalog for cross-cloud resources
    
    This service provides:
    - Centralized metadata management
    - Data classification
    - Resource discovery
    - Schema management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize metadata catalog
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.metadata: Dict[str, MetadataEntry] = {}
        
        logger.info("Metadata Catalog initialized")
    
    async def register_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        name: str,
        description: str,
        cloud: CloudProvider,
        region: str,
        owner: str,
        classification: DataClassification,
        schema: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> MetadataEntry:
        """
        Register resource in catalog
        
        Args:
            resource_id: Resource ID
            resource_type: Resource type
            name: Resource name
            description: Resource description
            cloud: Cloud provider
            region: Cloud region
            owner: Resource owner
            classification: Data classification
            schema: Resource schema
            tags: Resource tags
            properties: Additional properties
            
        Returns:
            Metadata entry
        """
        logger.info(f"Registering resource: {resource_id}")
        
        # Create metadata entry
        entry = MetadataEntry(
            resource_id=resource_id,
            resource_type=resource_type,
            name=name,
            description=description,
            cloud=cloud,
            region=region,
            owner=owner,
            status=MetadataStatus.ACTIVE,
            classification=classification,
            schema=schema,
            tags=tags or {},
            properties=properties or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store metadata
        self.metadata[resource_id] = entry
        
        logger.info(f"Resource registered: {resource_id}")
        return entry
    
    async def get_metadata(self, resource_id: str) -> Optional[MetadataEntry]:
        """
        Get metadata for resource
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Metadata entry if found, None otherwise
        """
        entry = self.metadata.get(resource_id)
        
        if entry:
            # Update last accessed
            entry.last_accessed = datetime.utcnow()
        
        return entry
    
    async def update_metadata(
        self,
        resource_id: str,
        updates: Dict[str, Any]
    ) -> Optional[MetadataEntry]:
        """
        Update resource metadata
        
        Args:
            resource_id: Resource ID
            updates: Updates to apply
            
        Returns:
            Updated metadata entry
        """
        entry = self.metadata.get(resource_id)
        if not entry:
            logger.warning(f"Resource not found: {resource_id}")
            return None
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        # Update timestamp
        entry.updated_at = datetime.utcnow()
        
        logger.info(f"Metadata updated: {resource_id}")
        return entry
    
    async def delete_resource(self, resource_id: str) -> bool:
        """
        Delete resource from catalog
        
        Args:
            resource_id: Resource ID
            
        Returns:
            True if deleted, False otherwise
        """
        if resource_id in self.metadata:
            del self.metadata[resource_id]
            logger.info(f"Resource deleted: {resource_id}")
            return True
        
        logger.warning(f"Resource not found: {resource_id}")
        return False
    
    async def search_resources(
        self,
        query: str,
        resource_type: Optional[ResourceType] = None,
        cloud: Optional[CloudProvider] = None,
        owner: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 100
    ) -> List[MetadataEntry]:
        """
        Search resources in catalog
        
        Args:
            query: Search query
            resource_type: Resource type filter
            cloud: Cloud provider filter
            owner: Owner filter
            tags: Tags filter
            limit: Maximum results
            
        Returns:
            List of matching metadata entries
        """
        results = list(self.metadata.values())
        
        # Apply filters
        if resource_type:
            results = [r for r in results if r.resource_type == resource_type]
        
        if cloud:
            results = [r for r in results if r.cloud == cloud]
        
        if owner:
            results = [r for r in results if r.owner == owner]
        
        if tags:
            for key, value in tags.items():
                results = [r for r in results if r.tags.get(key) == value]
        
        # Search in name and description
        if query:
            query_lower = query.lower()
            results = [
                r for r in results
                if query_lower in r.name.lower() or query_lower in r.description.lower()
            ]
        
        return results[:limit]
    
    async def get_resources_by_type(
        self,
        resource_type: ResourceType
    ) -> List[MetadataEntry]:
        """
        Get resources by type
        
        Args:
            resource_type: Resource type
            
        Returns:
            List of metadata entries
        """
        return [r for r in self.metadata.values() if r.resource_type == resource_type]
    
    async def get_resources_by_owner(
        self,
        owner: str
    ) -> List[MetadataEntry]:
        """
        Get resources by owner
        
        Args:
            owner: Resource owner
            
        Returns:
            List of metadata entries
        """
        return [r for r in self.metadata.values() if r.owner == owner]
    
    async def get_resources_by_cloud(
        self,
        cloud: CloudProvider
    ) -> List[MetadataEntry]:
        """
        Get resources by cloud
        
        Args:
            cloud: Cloud provider
            
        Returns:
            List of metadata entries
        """
        return [r for r in self.metadata.values() if r.cloud == cloud]
    
    async def get_classification_summary(self) -> Dict[str, int]:
        """
        Get data classification summary
        
        Returns:
            Count by classification
        """
        summary = {}
        
        for entry in self.metadata.values():
            sensitivity = entry.classification.sensitivity
            summary[sensitivity] = summary.get(sensitivity, 0) + 1
        
        return summary
    
    async def get_catalog_analytics(self) -> Dict[str, Any]:
        """
        Get catalog analytics
        
        Returns:
            Catalog statistics
        """
        total_resources = len(self.metadata)
        
        # By resource type
        by_type = {}
        for entry in self.metadata.values():
            resource_type = entry.resource_type.value
            by_type[resource_type] = by_type.get(resource_type, 0) + 1
        
        # By cloud
        by_cloud = {}
        for entry in self.metadata.values():
            cloud = entry.cloud.value
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By status
        by_status = {}
        for entry in self.metadata.values():
            status = entry.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By owner
        by_owner = {}
        for entry in self.metadata.values():
            owner = entry.owner
            by_owner[owner] = by_owner.get(owner, 0) + 1
        
        # PII/PHI resources
        pii_resources = len([r for r in self.metadata.values() if r.classification.pii])
        phi_resources = len([r for r in self.metadata.values() if r.classification.phi])
        
        return {
            "total_resources": total_resources,
            "by_type": by_type,
            "by_cloud": by_cloud,
            "by_status": by_status,
            "by_owner": by_owner,
            "pii_resources": pii_resources,
            "phi_resources": phi_resources
        }