"""
Azure Compute Service for Multi-Cloud Data Platform

This module provides Azure compute resource management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ComputeType(str, Enum):
    """Azure compute types"""
    VM = "vm"
    VMSS = "vmss"
    AKS = "aks"
    FUNCTIONS = "functions"
    DATABRICKS = "databricks"
    BATCH = "batch"


class ComputeState(str, Enum):
    """Compute states"""
    RUNNING = "running"
    STOPPED = "stopped"
    DEALLOCATED = "deallocated"
    FAILED = "failed"
    PROVISIONING = "provisioning"


class ComputeResource(BaseModel):
    """Azure compute resource"""
    resource_id: str
    name: str
    resource_group: str
    location: str
    compute_type: ComputeType
    state: ComputeState
    size: str
    vcpu_count: int
    memory_gb: int
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AzureComputeService:
    """
    Azure compute service
    
    This service provides:
    - Virtual machine management
    - AKS cluster management
    - Serverless functions
    - Databricks workspaces
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Azure compute service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resources: Dict[str, ComputeResource] = {}
        
        logger.info("Azure Compute Service initialized")
    
    async def create_compute(
        self,
        resource_id: str,
        name: str,
        resource_group: str,
        location: str,
        compute_type: ComputeType,
        size: str,
        vcpu_count: int,
        memory_gb: int,
        tags: Optional[Dict[str, str]] = None
    ) -> ComputeResource:
        """
        Create compute resource
        
        Args:
            resource_id: Resource ID
            name: Resource name
            resource_group: Resource group
            location: Azure region
            compute_type: Compute type
            size: VM/AKS size
            vcpu_count: VCPU count
            memory_gb: Memory in GB
            tags: Resource tags
            
        Returns:
            Compute resource
        """
        logger.info(f"Creating compute resource: {resource_id}")
        
        if resource_id in self.resources:
            raise ValueError(f"Compute resource already exists: {resource_id}")
        
        resource = ComputeResource(
            resource_id=resource_id,
            name=name,
            resource_group=resource_group,
            location=location,
            compute_type=compute_type,
            state=ComputeState.PROVISIONING,
            size=size,
            vcpu_count=vcpu_count,
            memory_gb=memory_gb,
            tags=tags or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.resources[resource_id] = resource
        
        logger.info(f"Compute resource created: {resource_id}")
        return resource
    
    async def get_compute(self, resource_id: str) -> Optional[ComputeResource]:
        """
        Get compute resource by ID
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Compute resource if found, None otherwise
        """
        return self.resources.get(resource_id)
    
    async def list_compute(
        self,
        compute_type: Optional[ComputeType] = None,
        resource_group: Optional[str] = None,
        state: Optional[ComputeState] = None
    ) -> List[ComputeResource]:
        """
        List compute resources
        
        Args:
            compute_type: Compute type filter
            resource_group: Resource group filter
            state: State filter
            
        Returns:
            List of compute resources
        """
        resources = list(self.resources.values())
        
        if compute_type:
            resources = [r for r in resources if r.compute_type == compute_type]
        
        if resource_group:
            resources = [r for r in resources if r.resource_group == resource_group]
        
        if state:
            resources = [r for r in resources if r.state == state]
        
        return resources
    
    async def update_state(self, resource_id: str, state: ComputeState) -> Optional[ComputeResource]:
        """
        Update compute resource state
        
        Args:
            resource_id: Resource ID
            state: New state
            
        Returns:
            Updated compute resource
        """
        resource = self.resources.get(resource_id)
        if not resource:
            logger.warning(f"Compute resource not found: {resource_id}")
            return None
        
        resource.state = state
        resource.updated_at = datetime.utcnow()
        
        logger.info(f"Compute resource state updated: {resource_id} -> {state}")
        return resource
    
    async def scale_compute(
        self,
        resource_id: str,
        instance_count: int
    ) -> Dict[str, Any]:
        """
        Scale compute resource
        
        Args:
            resource_id: Resource ID
            instance_count: Target instance count
            
        Returns:
            Scale operation details
        """
        resource = self.resources.get(resource_id)
        if not resource:
            raise ValueError(f"Compute resource not found: {resource_id}")
        
        logger.info(f"Scaling compute resource: {resource_id} to {instance_count} instances")
        
        return {
            "resource_id": resource_id,
            "name": resource.name,
            "target_instance_count": instance_count,
            "operation": "scale",
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat()
        }
    
    async def delete_compute(self, resource_id: str) -> bool:
        """
        Delete compute resource
        
        Args:
            resource_id: Resource ID
            
        Returns:
            True if deleted, False otherwise
        """
        if resource_id in self.resources:
            del self.resources[resource_id]
            logger.info(f"Compute resource deleted: {resource_id}")
            return True
        
        logger.warning(f"Compute resource not found: {resource_id}")
        return False
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get compute analytics
        
        Returns:
            Compute statistics
        """
        total_resources = len(self.resources)
        
        # By compute type
        by_type = {}
        for resource in self.resources.values():
            compute_type = resource.compute_type.value
            by_type[compute_type] = by_type.get(compute_type, 0) + 1
        
        # By state
        by_state = {}
        for resource in self.resources.values():
            state = resource.state.value
            by_state[state] = by_state.get(state, 0) + 1
        
        # By location
        by_location = {}
        for resource in self.resources.values():
            location = resource.location
            by_location[location] = by_location.get(location, 0) + 1
        
        # Total capacity
        total_vcpu = sum(r.vcpu_count for r in self.resources.values())
        total_memory = sum(r.memory_gb for r in self.resources.values())
        
        return {
            "total_resources": total_resources,
            "total_vcpu": total_vcpu,
            "total_memory_gb": total_memory,
            "by_type": by_type,
            "by_state": by_state,
            "by_location": by_location
        }