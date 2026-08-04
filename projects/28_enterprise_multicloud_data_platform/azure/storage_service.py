"""
Azure Storage Service for Multi-Cloud Data Platform

This module provides Azure Blob Storage integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StorageType(str, Enum):
    """Azure storage types"""
    BLOB = "blob"
    ADLS = "adls"
    FILE = "file"
    QUEUE = "queue"
    TABLE = "table"


class AccessTier(str, Enum):
    """Azure storage access tiers"""
    HOT = "hot"
    COOL = "cool"
    ARCHIVE = "archive"


class StorageAccount(BaseModel):
    """Azure storage account"""
    account_id: str
    name: str
    resource_group: str
    location: str
    storage_type: StorageType
    access_tier: AccessTier
    enable_https: bool = True
    allow_public_access: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AzureStorageService:
    """
    Azure Blob Storage service
    
    This service provides:
    - Storage account management
    - Container/Blob operations
    - Access control
    - Lifecycle management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Azure storage service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.storage_accounts: Dict[str, StorageAccount] = {}
        
        logger.info("Azure Storage Service initialized")
    
    async def create_storage_account(
        self,
        account_id: str,
        name: str,
        resource_group: str,
        location: str,
        storage_type: StorageType = StorageType.BLOB,
        access_tier: AccessTier = AccessTier.HOT,
        enable_https: bool = True,
        allow_public_access: bool = False,
        tags: Optional[Dict[str, str]] = None
    ) -> StorageAccount:
        """
        Create storage account
        
        Args:
            account_id: Account ID
            name: Storage account name
            resource_group: Resource group
            location: Azure region
            storage_type: Storage type
            access_tier: Access tier
            enable_https: Enable HTTPS
            allow_public_access: Allow public access
            tags: Resource tags
            
        Returns:
            Storage account
        """
        logger.info(f"Creating storage account: {account_id}")
        
        if account_id in self.storage_accounts:
            raise ValueError(f"Storage account already exists: {account_id}")
        
        account = StorageAccount(
            account_id=account_id,
            name=name,
            resource_group=resource_group,
            location=location,
            storage_type=storage_type,
            access_tier=access_tier,
            enable_https=enable_https,
            allow_public_access=allow_public_access,
            tags=tags or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.storage_accounts[account_id] = account
        
        logger.info(f"Storage account created: {account_id}")
        return account
    
    async def get_storage_account(self, account_id: str) -> Optional[StorageAccount]:
        """
        Get storage account by ID
        
        Args:
            account_id: Account ID
            
        Returns:
            Storage account if found, None otherwise
        """
        return self.storage_accounts.get(account_id)
    
    async def list_storage_accounts(
        self,
        resource_group: Optional[str] = None,
        storage_type: Optional[StorageType] = None
    ) -> List[StorageAccount]:
        """
        List storage accounts
        
        Args:
            resource_group: Resource group filter
            storage_type: Storage type filter
            
        Returns:
            List of storage accounts
        """
        accounts = list(self.storage_accounts.values())
        
        if resource_group:
            accounts = [a for a in accounts if a.resource_group == resource_group]
        
        if storage_type:
            accounts = [a for a in accounts if a.storage_type == storage_type]
        
        return accounts
    
    async def create_container(
        self,
        account_id: str,
        container_name: str,
        public_access: bool = False
    ) -> Dict[str, Any]:
        """
        Create blob container
        
        Args:
            account_id: Storage account ID
            container_name: Container name
            public_access: Allow public access
            
        Returns:
            Container information
        """
        account = self.storage_accounts.get(account_id)
        if not account:
            raise ValueError(f"Storage account not found: {account_id}")
        
        logger.info(f"Creating container: {container_name} in {account_id}")
        
        container = {
            "container_id": f"{account_id}/{container_name}",
            "account_id": account_id,
            "name": container_name,
            "public_access": public_access,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return container
    
    async def upload_blob(
        self,
        account_id: str,
        container_name: str,
        blob_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload blob
        
        Args:
            account_id: Storage account ID
            container_name: Container name
            blob_name: Blob name
            content: Blob content
            content_type: Content type
            metadata: Blob metadata
            
        Returns:
            Blob information
        """
        account = self.storage_accounts.get(account_id)
        if not account:
            raise ValueError(f"Storage account not found: {account_id}")
        
        logger.info(f"Uploading blob: {blob_name} to {account_id}/{container_name}")
        
        blob = {
            "blob_id": f"{account_id}/{container_name}/{blob_name}",
            "account_id": account_id,
            "container": container_name,
            "name": blob_name,
            "size_bytes": len(content),
            "content_type": content_type,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        return blob
    
    async def download_blob(
        self,
        account_id: str,
        container_name: str,
        blob_name: str
    ) -> Dict[str, Any]:
        """
        Download blob (metadata)
        
        Args:
            account_id: Storage account ID
            container_name: Container name
            blob_name: Blob name
            
        Returns:
            Blob metadata
        """
        logger.info(f"Downloading blob: {blob_name}")
        
        return {
            "blob_id": f"{account_id}/{container_name}/{blob_name}",
            "account_id": account_id,
            "container": container_name,
            "name": blob_name,
            "content_type": "application/octet-stream"
        }
    
    async def delete_storage_account(self, account_id: str) -> bool:
        """
        Delete storage account
        
        Args:
            account_id: Account ID
            
        Returns:
            True if deleted, False otherwise
        """
        if account_id in self.storage_accounts:
            del self.storage_accounts[account_id]
            logger.info(f"Storage account deleted: {account_id}")
            return True
        
        logger.warning(f"Storage account not found: {account_id}")
        return False
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get storage analytics
        
        Returns:
            Storage statistics
        """
        total_accounts = len(self.storage_accounts)
        
        # By type
        by_type = {}
        for account in self.storage_accounts.values():
            storage_type = account.storage_type.value
            by_type[storage_type] = by_type.get(storage_type, 0) + 1
        
        # By tier
        by_tier = {}
        for account in self.storage_accounts.values():
            tier = account.access_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1
        
        # By location
        by_location = {}
        for account in self.storage_accounts.values():
            location = account.location
            by_location[location] = by_location.get(location, 0) + 1
        
        return {
            "total_storage_accounts": total_accounts,
            "by_type": by_type,
            "by_tier": by_tier,
            "by_location": by_location
        }