"""
Discovery Service for Cross-Cloud Data Management

This module provides resource discovery across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider
from .metadata_catalog import MetadataCatalog, ResourceType

logger = logging.getLogger(__name__)


class DiscoveryStatus(str, Enum):
    """Discovery status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryJob(BaseModel):
    """Discovery job"""
    job_id: str
    name: str
    description: str
    cloud: Optional[CloudProvider] = None
    resource_types: List[ResourceType]
    status: DiscoveryStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    discovered_count: int = 0
    errors: List[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime


class DiscoveryService:
    """
    Cross-cloud resource discovery service
    
    This service provides:
    - Automated resource discovery
    - Resource inventory
    - Change detection
    - Resource mapping
    """
    
    def __init__(self, config: Dict, metadata_catalog: MetadataCatalog):
        """
        Initialize discovery service
        
        Args:
            config: Configuration dictionary
            metadata_catalog: Metadata catalog instance
        """
        self.config = config
        self.metadata_catalog = metadata_catalog
        self.jobs: Dict[str, DiscoveryJob] = {}
        
        logger.info("Discovery Service initialized")
    
    async def create_discovery_job(
        self,
        name: str,
        description: str,
        cloud: Optional[CloudProvider],
        resource_types: List[ResourceType],
        created_by: str
    ) -> DiscoveryJob:
        """
        Create discovery job
        
        Args:
            name: Job name
            description: Job description
            cloud: Cloud provider (optional for all)
            resource_types: Resource types to discover
            created_by: User who created
            
        Returns:
            Discovery job
        """
        logger.info(f"Creating discovery job: {name}")
        
        # Generate job ID
        job_id = f"discovery-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create job
        job = DiscoveryJob(
            job_id=job_id,
            name=name,
            description=description,
            cloud=cloud,
            resource_types=resource_types,
            status=DiscoveryStatus.PENDING,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        # Store job
        self.jobs[job_id] = job
        
        logger.info(f"Discovery job created: {job_id}")
        return job
    
    async def run_discovery_job(self, job_id: str) -> Optional[DiscoveryJob]:
        """
        Run discovery job
        
        Args:
            job_id: Job ID
            
        Returns:
            Updated discovery job
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Discovery job not found: {job_id}")
            return None
        
        logger.info(f"Running discovery job: {job_id}")
        
        # Update job status
        job.status = DiscoveryStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        
        try:
            # Discover resources
            discovered_resources = await self._discover_resources(job)
            
            # Register resources in catalog
            for resource in discovered_resources:
                try:
                    await self.metadata_catalog.register_resource(**resource)
                    job.discovered_count += 1
                except Exception as e:
                    job.errors.append(f"Failed to register resource: {str(e)}")
            
            # Update job status
            job.status = DiscoveryStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            logger.info(f"Discovery job completed: {job_id} ({job.discovered_count} resources)")
            
        except Exception as e:
            job.status = DiscoveryStatus.FAILED
            job.errors.append(str(e))
            logger.error(f"Discovery job failed: {job_id} - {e}")
        
        return job
    
    async def _discover_resources(self, job: DiscoveryJob) -> List[Dict[str, Any]]:
        """
        Discover resources based on job configuration
        
        Args:
            job: Discovery job
            
        Returns:
            List of discovered resources
        """
        resources = []
        
        # Determine clouds to scan
        clouds = [job.cloud] if job.cloud else [CloudProvider.AZURE, CloudProvider.AWS]
        
        # Discover resources for each cloud
        for cloud in clouds:
            for resource_type in job.resource_types:
                try:
                    cloud_resources = await self._discover_cloud_resources(
                        cloud,
                        resource_type
                    )
                    resources.extend(cloud_resources)
                    
                except Exception as e:
                    job.errors.append(f"Failed to discover {resource_type.value} in {cloud}: {str(e)}")
        
        return resources
    
    async def _discover_cloud_resources(
        self,
        cloud: CloudProvider,
        resource_type: ResourceType
    ) -> List[Dict[str, Any]]:
        """
        Discover resources in cloud
        
        Args:
            cloud: Cloud provider
            resource_type: Resource type
            
        Returns:
            List of resources
        """
        # In real implementation:
        # - Azure: Use Azure SDK to query resources
        # - AWS: Use boto3 to query resources
        
        # Mock implementation
        mock_resources = []
        
        if resource_type == ResourceType.STORAGE:
            mock_resources.append({
                "resource_id": f"{cloud.value}-storage-001",
                "resource_type": resource_type,
                "name": f"{cloud.value}-storage",
                "description": f"Storage account in {cloud.value}",
                "cloud": cloud,
                "region": "eastus",
                "owner": "platform-team",
                "classification": {
                    "sensitivity": "internal",
                    "pii": False,
                    "phi": False,
                    "pci": False
                }
            })
        
        elif resource_type == ResourceType.DATABASE:
            mock_resources.append({
                "resource_id": f"{cloud.value}-db-001",
                "resource_type": resource_type,
                "name": f"{cloud.value}-database",
                "description": f"Database in {cloud.value}",
                "cloud": cloud,
                "region": "eastus",
                "owner": "data-team",
                "classification": {
                    "sensitivity": "confidential",
                    "pii": True,
                    "phi": False,
                    "pci": False
                }
            })
        
        elif resource_type == ResourceType.TOPIC:
            mock_resources.append({
                "resource_id": f"{cloud.value}-topic-001",
                "resource_type": resource_type,
                "name": f"{cloud.value}-topic",
                "description": f"Kafka topic in {cloud.value}",
                "cloud": cloud,
                "region": "eastus",
                "owner": "streaming-team",
                "classification": {
                    "sensitivity": "internal",
                    "pii": False,
                    "phi": False,
                    "pci": False
                }
            })
        
        return mock_resources
    
    async def get_job(self, job_id: str) -> Optional[DiscoveryJob]:
        """
        Get discovery job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Discovery job if found, None otherwise
        """
        return self.jobs.get(job_id)
    
    async def list_jobs(
        self,
        status: Optional[DiscoveryStatus] = None,
        created_by: Optional[str] = None
    ) -> List[DiscoveryJob]:
        """
        List discovery jobs
        
        Args:
            status: Status filter (optional)
            created_by: Creator filter (optional)
            
        Returns:
            List of discovery jobs
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if created_by:
            jobs = [j for j in jobs if j.created_by == created_by]
        
        # Sort by created_at desc
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs
    
    async def get_resource_inventory(
        self,
        cloud: Optional[CloudProvider] = None,
        resource_type: Optional[ResourceType] = None
    ) -> Dict[str, Any]:
        """
        Get resource inventory
        
        Args:
            cloud: Cloud provider (optional)
            resource_type: Resource type (optional)
            
        Returns:
            Resource inventory
        """
        # Get all resources from catalog
        resources = []
        
        if cloud:
            resources = await self.metadata_catalog.get_resources_by_cloud(cloud)
        else:
            # Get all resources
            resources = list(self.metadata_catalog.metadata.values())
        
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        
        # Build inventory
        inventory = {
            "total_resources": len(resources),
            "by_cloud": {},
            "by_type": {},
            "by_status": {},
            "by_owner": {},
            "resources": []
        }
        
        for resource in resources:
            # By cloud
            cloud_name = resource.cloud.value
            inventory["by_cloud"][cloud_name] = inventory["by_cloud"].get(cloud_name, 0) + 1
            
            # By type
            resource_type_name = resource.resource_type.value
            inventory["by_type"][resource_type_name] = inventory["by_type"].get(resource_type_name, 0) + 1
            
            # By status
            status_name = resource.status.value
            inventory["by_status"][status_name] = inventory["by_status"].get(status_name, 0) + 1
            
            # By owner
            owner = resource.owner
            inventory["by_owner"][owner] = inventory["by_owner"].get(owner, 0) + 1
            
            # Add resource
            inventory["resources"].append({
                "resource_id": resource.resource_id,
                "name": resource.name,
                "type": resource.resource_type.value,
                "cloud": resource.cloud.value,
                "region": resource.region,
                "owner": resource.owner,
                "status": resource.status.value
            })
        
        return inventory
    
    async def detect_changes(
        self,
        cloud: Optional[CloudProvider] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect resource changes
        
        Args:
            cloud: Cloud provider (optional)
            
        Returns:
            List of changes
        """
        # In real implementation:
        # - Compare current state with previous state
        # - Identify new, modified, deleted resources
        
        changes = []
        
        # Mock implementation
        changes.append({
            "change_type": "created",
            "resource_id": "azure-storage-001",
            "resource_type": "storage",
            "cloud": "azure",
            "detected_at": datetime.utcnow().isoformat()
        })
        
        return changes
    
    async def get_discovery_analytics(self) -> Dict[str, Any]:
        """
        Get discovery analytics
        
        Returns:
            Discovery statistics
        """
        total_jobs = len(self.jobs)
        
        # By status
        by_status = {}
        for job in self.jobs.values():
            status = job.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # Total discovered resources
        total_discovered = sum(job.discovered_count for job in self.jobs.values())
        
        # By cloud
        by_cloud = {}
        for job in self.jobs.values():
            if job.cloud:
                cloud_name = job.cloud.value
                by_cloud[cloud_name] = by_cloud.get(cloud_name, 0) + job.discovered_count
        
        return {
            "total_jobs": total_jobs,
            "by_status": by_status,
            "total_discovered_resources": total_discovered,
            "by_cloud": by_cloud
        }