"""
Cross-Cloud Role Mapper for Identity Federation

This module provides role mapping and synchronization across Azure and AWS.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
import logging
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider, UserIdentity

logger = logging.getLogger(__name__)


class Permission(BaseModel):
    """Unified permission definition"""
    permission_id: str
    name: str
    description: str
    resource_type: str
    actions: List[str]
    conditions: Dict[str, str] = Field(default_factory=dict)


class CloudRole(BaseModel):
    """Cloud-specific role definition"""
    role_id: str
    name: str
    cloud: CloudProvider
    description: str
    permissions: List[str] = Field(default_factory=list)
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime


class RoleMapping(BaseModel):
    """Role mapping between clouds"""
    mapping_id: str
    logical_role: str
    azure_role: Optional[str] = None
    aws_role: Optional[str] = None
    description: str
    created_at: datetime
    updated_at: datetime


class CrossCloudRoleMapper:
    """
    Cross-cloud role mapping and synchronization service
    
    This service provides:
    - Role mapping between Azure and AWS
    - Permission synchronization
    - Just-in-time role assignment
    - Role inheritance
    """
    
    def __init__(self, config: Dict):
        """
        Initialize role mapper
        
        Args:
            config: Configuration dictionary containing:
                - role_mappings: Pre-defined role mappings
                - permission_sets: Available permissions
        """
        self.config = config
        self.role_mappings: Dict[str, RoleMapping] = {}
        self.cloud_roles: Dict[str, CloudRole] = {}
        self.permissions: Dict[str, Permission] = {}
        
        # Load default role mappings
        self._load_default_role_mappings()
        
        logger.info("Cross-Cloud Role Mapper initialized")
    
    def _load_default_role_mappings(self) -> None:
        """Load default role mappings"""
        default_mappings = [
            RoleMapping(
                mapping_id="data-engineer",
                logical_role="data-engineer",
                azure_role="Data Engineer",
                aws_role="DataEngineerAccess",
                description="Data engineering role with access to data platforms",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            RoleMapping(
                mapping_id="ml-engineer",
                logical_role="ml-engineer",
                azure_role="ML Engineer",
                aws_role="MLEngineerAccess",
                description="ML engineering role with access to ML platforms",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            RoleMapping(
                mapping_id="platform-admin",
                logical_role="platform-admin",
                azure_role="Platform Administrator",
                aws_role="PlatformAdminAccess",
                description="Platform administration with full access",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            RoleMapping(
                mapping_id="data-consumer",
                logical_role="data-consumer",
                azure_role="Data Reader",
                aws_role="DataConsumerAccess",
                description="Read-only access to data platforms",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            RoleMapping(
                mapping_id="analytics-engineer",
                logical_role="analytics-engineer",
                azure_role="Analytics Engineer",
                aws_role="AnalyticsEngineerAccess",
                description="Analytics engineering with query and dashboard access",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for mapping in default_mappings:
            self.role_mappings[mapping.mapping_id] = mapping
    
    async def create_role_mapping(
        self,
        mapping: RoleMapping
    ) -> RoleMapping:
        """
        Create new role mapping
        
        Args:
            mapping: Role mapping configuration
            
        Returns:
            Created role mapping
        """
        logger.info(f"Creating role mapping: {mapping.mapping_id}")
        
        if mapping.mapping_id in self.role_mappings:
            raise ValueError(f"Role mapping already exists: {mapping.mapping_id}")
        
        self.role_mappings[mapping.mapping_id] = mapping
        
        logger.info(f"Role mapping created: {mapping.mapping_id}")
        return mapping
    
    async def get_role_mapping(
        self,
        mapping_id: str
    ) -> Optional[RoleMapping]:
        """
        Get role mapping by ID
        
        Args:
            mapping_id: Mapping ID
            
        Returns:
            Role mapping if found, None otherwise
        """
        return self.role_mappings.get(mapping_id)
    
    async def get_cloud_role(
        self,
        user: UserIdentity,
        cloud: CloudProvider
    ) -> Optional[CloudRole]:
        """
        Get cloud-specific role for user
        
        Args:
            user: User identity
            cloud: Cloud provider
            
        Returns:
            Cloud role if found, None otherwise
        """
        # Get user's logical roles
        logical_roles = user.roles.get("global", [])
        
        # Find first matching role mapping
        for logical_role in logical_roles:
            mapping = await self.get_role_mapping(logical_role)
            if mapping:
                # Get cloud-specific role
                cloud_role_name = (
                    mapping.azure_role if cloud == CloudProvider.AZURE
                    else mapping.aws_role
                )
                
                if cloud_role_name:
                    # Return cloud role
                    return await self._get_cloud_role_by_name(
                        cloud_role_name,
                        cloud
                    )
        
        return None
    
    async def _get_cloud_role_by_name(
        self,
        role_name: str,
        cloud: CloudProvider
    ) -> Optional[CloudRole]:
        """
        Get cloud role by name
        
        Args:
            role_name: Role name
            cloud: Cloud provider
            
        Returns:
            Cloud role if found, None otherwise
        """
        # In real implementation, query cloud provider
        # For now, return from cache
        for role in self.cloud_roles.values():
            if role.name == role_name and role.cloud == cloud:
                return role
        
        return None
    
    async def assign_roles_to_user(
        self,
        user: UserIdentity,
        logical_roles: List[str],
        clouds: List[CloudProvider]
    ) -> Dict[str, List[str]]:
        """
        Assign roles to user across clouds
        
        Args:
            user: User identity
            logical_roles: List of logical roles
            clouds: List of cloud providers
            
        Returns:
            Assigned roles by cloud
        """
        logger.info(f"Assigning roles to user {user.user_id}: {logical_roles}")
        
        assigned_roles = {}
        
        for cloud in clouds:
            cloud_roles = []
            
            for logical_role in logical_roles:
                mapping = await self.get_role_mapping(logical_role)
                if not mapping:
                    continue
                
                # Get cloud-specific role
                cloud_role_name = (
                    mapping.azure_role if cloud == CloudProvider.AZURE
                    else mapping.aws_role
                )
                
                if cloud_role_name:
                    # Assign role in cloud
                    await self._assign_cloud_role(user, cloud_role_name, cloud)
                    cloud_roles.append(cloud_role_name)
            
            assigned_roles[cloud.value] = cloud_roles
        
        # Update user roles
        user.roles = assigned_roles
        
        logger.info(f"Roles assigned to user {user.user_id}")
        return assigned_roles
    
    async def _assign_cloud_role(
        self,
        user: UserIdentity,
        role_name: str,
        cloud: CloudProvider
    ) -> None:
        """
        Assign role in specific cloud
        
        Args:
            user: User identity
            role_name: Role name
            cloud: Cloud provider
        """
        # In real implementation:
        # - Azure: Assign RBAC role using Azure SDK
        # - AWS: Attach IAM policy using boto3
        
        logger.info(f"Assigned role {role_name} to user {user.user_id} in {cloud}")
    
    async def revoke_roles_from_user(
        self,
        user: UserIdentity,
        clouds: Optional[List[CloudProvider]] = None
    ) -> None:
        """
        Revoke all roles from user
        
        Args:
            user: User identity
            clouds: Cloud providers (optional, all if not specified)
        """
        logger.info(f"Revoking roles from user: {user.user_id}")
        
        clouds_to_revoke = clouds or [CloudProvider.AZURE, CloudProvider.AWS]
        
        for cloud in clouds_to_revoke:
            cloud_roles = user.roles.get(cloud.value, [])
            
            for role_name in cloud_roles:
                await self._revoke_cloud_role(user, role_name, cloud)
        
        # Clear user roles
        user.roles = {}
        
        logger.info(f"Roles revoked from user: {user.user_id}")
    
    async def _revoke_cloud_role(
        self,
        user: UserIdentity,
        role_name: str,
        cloud: CloudProvider
    ) -> None:
        """
        Revoke role in specific cloud
        
        Args:
            user: User identity
            role_name: Role name
            cloud: Cloud provider
        """
        # In real implementation:
        # - Azure: Remove RBAC role assignment
        # - AWS: Detach IAM policy
        
        logger.info(f"Revoked role {role_name} from user {user.user_id} in {cloud}")
    
    async def list_available_roles(
        self,
        cloud: Optional[CloudProvider] = None
    ) -> List[CloudRole]:
        """
        List available roles
        
        Args:
            cloud: Cloud provider (optional, all if not specified)
            
        Returns:
            List of available roles
        """
        if cloud:
            return [r for r in self.cloud_roles.values() if r.cloud == cloud]
        return list(self.cloud_roles.values())
    
    async def list_role_mappings(
        self,
        cloud: Optional[CloudProvider] = None
    ) -> List[RoleMapping]:
        """
        List role mappings
        
        Args:
            cloud: Cloud provider (optional, all if not specified)
            
        Returns:
            List of role mappings
        """
        mappings = list(self.role_mappings.values())
        
        if cloud == CloudProvider.AZURE:
            return [m for m in mappings if m.azure_role]
        elif cloud == CloudProvider.AWS:
            return [m for m in mappings if m.aws_role]
        
        return mappings
    
    async def get_permissions_for_role(
        self,
        role_name: str,
        cloud: CloudProvider
    ) -> List[Permission]:
        """
        Get permissions for role
        
        Args:
            role_name: Role name
            cloud: Cloud provider
            
        Returns:
            List of permissions
        """
        # Get cloud role
        cloud_role = await self._get_cloud_role_by_name(role_name, cloud)
        if not cloud_role:
            return []
        
        # Get permissions
        permissions = []
        for perm_id in cloud_role.permissions:
            perm = self.permissions.get(perm_id)
            if perm:
                permissions.append(perm)
        
        return permissions
    
    async def create_permission(
        self,
        permission: Permission
    ) -> Permission:
        """
        Create new permission
        
        Args:
            permission: Permission definition
            
        Returns:
            Created permission
        """
        logger.info(f"Creating permission: {permission.permission_id}")
        
        if permission.permission_id in self.permissions:
            raise ValueError(f"Permission already exists: {permission.permission_id}")
        
        self.permissions[permission.permission_id] = permission
        
        logger.info(f"Permission created: {permission.permission_id}")
        return permission
    
    async def sync_roles(
        self,
        source_cloud: CloudProvider,
        target_cloud: CloudProvider
    ) -> Dict[str, List[str]]:
        """
        Synchronize roles from source to target cloud
        
        Args:
            source_cloud: Source cloud provider
            target_cloud: Target cloud provider
            
        Returns:
            Synchronization results
        """
        logger.info(f"Syncing roles from {source_cloud} to {target_cloud}")
        
        results = {
            "synced": [],
            "failed": []
        }
        
        # Get all role mappings
        for mapping in self.role_mappings.values():
            source_role = (
                mapping.azure_role if source_cloud == CloudProvider.AZURE
                else mapping.aws_role
            )
            target_role = (
                mapping.azure_role if target_cloud == CloudProvider.AZURE
                else mapping.aws_role
            )
            
            if not source_role or not target_role:
                continue
            
            try:
                # Get source role permissions
                permissions = await self.get_permissions_for_role(
                    source_role,
                    source_cloud
                )
                
                # Create/update target role
                await self._sync_role_to_cloud(
                    target_role,
                    target_cloud,
                    permissions
                )
                
                results["synced"].append(target_role)
                
            except Exception as e:
                logger.error(f"Failed to sync role {target_role}: {e}")
                results["failed"].append(target_role)
        
        return results
    
    async def _sync_role_to_cloud(
        self,
        role_name: str,
        cloud: CloudProvider,
        permissions: List[Permission]
    ) -> None:
        """
        Sync role to cloud
        
        Args:
            role_name: Role name
            cloud: Cloud provider
            permissions: List of permissions
        """
        # In real implementation:
        # - Create/update role in cloud provider
        # - Assign permissions to role
        
        logger.info(f"Synced role {role_name} to {cloud}")
    
    async def get_role_hierarchy(
        self,
        role_name: str,
        cloud: CloudProvider
    ) -> Dict[str, Set[str]]:
        """
        Get role hierarchy (inheritance)
        
        Args:
            role_name: Role name
            cloud: Cloud provider
            
        Returns:
            Role hierarchy with inherited roles
        """
        hierarchy = {
            "direct": set(),
            "inherited": set()
        }
        
        # Get cloud role
        cloud_role = await self._get_cloud_role_by_name(role_name, cloud)
        if not cloud_role:
            return hierarchy
        
        # Add direct permissions
        hierarchy["direct"] = set(cloud_role.permissions)
        
        # In real implementation, resolve role inheritance
        # For now, return empty inherited set
        
        return hierarchy
    
    async def validate_role_assignment(
        self,
        user: UserIdentity,
        role_name: str,
        cloud: CloudProvider
    ) -> bool:
        """
        Validate if user can be assigned role
        
        Args:
            user: User identity
            role_name: Role name
            cloud: Cloud provider
            
        Returns:
            True if assignment is valid, False otherwise
        """
        # Get role
        cloud_role = await self._get_cloud_role_by_name(role_name, cloud)
        if not cloud_role:
            return False
        
        # Check if user already has role
        user_roles = user.roles.get(cloud.value, [])
        if role_name in user_roles:
            logger.warning(f"User {user.user_id} already has role {role_name}")
            return False
        
        # In real implementation, check:
        # - User attributes
        # - Role constraints
        # - Approval requirements
        
        return True
    
    async def get_role_analytics(
        self
    ) -> Dict[str, int]:
        """
        Get role analytics
        
        Returns:
            Role statistics
        """
        return {
            "total_mappings": len(self.role_mappings),
            "total_cloud_roles": len(self.cloud_roles),
            "total_permissions": len(self.permissions),
            "azure_roles": len([r for r in self.cloud_roles.values() if r.cloud == CloudProvider.AZURE]),
            "aws_roles": len([r for r in self.cloud_roles.values() if r.cloud == CloudProvider.AWS])
        }