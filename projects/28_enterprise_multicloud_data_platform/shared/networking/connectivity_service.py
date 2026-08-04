"""
Connectivity Service for Cross-Cloud Platform

This module provides cross-cloud connectivity management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    """Connection types"""
    SITE_TO_SITE_VPN = "site_to_site_vpn"
    POINT_TO_SITE_VPN = "point_to_site_vpn"
    EXPRESS_ROUTE = "express_route"
    DIRECT_CONNECT = "direct_connect"
    PEERING = "peering"
    TRANSIT = "transit"


class ConnectionStatus(str, Enum):
    """Connection status"""
    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class Connection(BaseModel):
    """Connection definition"""
    connection_id: str
    name: str
    connection_type: ConnectionType
    source_cloud: str
    source_region: str
    target_cloud: str
    target_region: str
    bandwidth: str  # e.g., "1Gbps", "10Gbps"
    status: ConnectionStatus
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ConnectivityService:
    """
    Cross-cloud connectivity service
    
    This service provides:
    - Cross-cloud network connectivity
    - VPN management
    - Peering configuration
    - Bandwidth management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize connectivity service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.connections: Dict[str, Connection] = {}
        
        logger.info("Connectivity Service initialized")
    
    async def create_connection(
        self,
        connection_id: str,
        name: str,
        connection_type: ConnectionType,
        source_cloud: str,
        source_region: str,
        target_cloud: str,
        target_region: str,
        bandwidth: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Connection:
        """
        Create cross-cloud connection
        
        Args:
            connection_id: Connection ID
            name: Connection name
            connection_type: Connection type
            source_cloud: Source cloud provider
            source_region: Source region
            target_cloud: Target cloud provider
            target_region: Target region
            bandwidth: Bandwidth
            properties: Additional properties
            
        Returns:
            Connection
        """
        logger.info(f"Creating connection: {connection_id}")
        
        if connection_id in self.connections:
            raise ValueError(f"Connection already exists: {connection_id}")
        
        connection = Connection(
            connection_id=connection_id,
            name=name,
            connection_type=connection_type,
            source_cloud=source_cloud,
            source_region=source_region,
            target_cloud=target_cloud,
            target_region=target_region,
            bandwidth=bandwidth,
            status=ConnectionStatus.PENDING,
            properties=properties or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.connections[connection_id] = connection
        
        logger.info(f"Connection created: {connection_id}")
        return connection
    
    async def get_connection(self, connection_id: str) -> Optional[Connection]:
        """
        Get connection by ID
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Connection if found, None otherwise
        """
        return self.connections.get(connection_id)
    
    async def update_connection_status(
        self,
        connection_id: str,
        status: ConnectionStatus
    ) -> Optional[Connection]:
        """
        Update connection status
        
        Args:
            connection_id: Connection ID
            status: New status
            
        Returns:
            Updated connection
        """
        connection = self.connections.get(connection_id)
        if not connection:
            logger.warning(f"Connection not found: {connection_id}")
            return None
        
        connection.status = status
        connection.updated_at = datetime.utcnow()
        
        logger.info(f"Connection status updated: {connection_id} -> {status}")
        return connection
    
    async def list_connections(
        self,
        source_cloud: Optional[str] = None,
        target_cloud: Optional[str] = None,
        connection_type: Optional[ConnectionType] = None,
        status: Optional[ConnectionStatus] = None
    ) -> List[Connection]:
        """
        List connections
        
        Args:
            source_cloud: Source cloud filter
            target_cloud: Target cloud filter
            connection_type: Connection type filter
            status: Status filter
            
        Returns:
            List of connections
        """
        connections = list(self.connections.values())
        
        if source_cloud:
            connections = [c for c in connections if c.source_cloud == source_cloud]
        
        if target_cloud:
            connections = [c for c in connections if c.target_cloud == target_cloud]
        
        if connection_type:
            connections = [c for c in connections if c.connection_type == connection_type]
        
        if status:
            connections = [c for c in connections if c.status == status]
        
        return connections
    
    async def delete_connection(self, connection_id: str) -> bool:
        """
        Delete connection
        
        Args:
            connection_id: Connection ID
            
        Returns:
            True if deleted, False otherwise
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.info(f"Connection deleted: {connection_id}")
            return True
        
        logger.warning(f"Connection not found: {connection_id}")
        return False
    
    async def get_connectivity_matrix(self) -> Dict[str, Any]:
        """
        Get connectivity matrix
        
        Returns:
            Connectivity matrix
        """
        matrix = {
            "total_connections": len(self.connections),
            "by_status": {},
            "by_type": {},
            "by_source_cloud": {},
            "by_target_cloud": {},
            "connections": []
        }
        
        for connection in self.connections.values():
            # By status
            status = connection.status.value
            matrix["by_status"][status] = matrix["by_status"].get(status, 0) + 1
            
            # By type
            conn_type = connection.connection_type.value
            matrix["by_type"][conn_type] = matrix["by_type"].get(conn_type, 0) + 1
            
            # By source cloud
            source = connection.source_cloud
            matrix["by_source_cloud"][source] = matrix["by_source_cloud"].get(source, 0) + 1
            
            # By target cloud
            target = connection.target_cloud
            matrix["by_target_cloud"][target] = matrix["by_target_cloud"].get(target, 0) + 1
            
            # Add connection
            matrix["connections"].append({
                "connection_id": connection.connection_id,
                "name": connection.name,
                "type": connection.connection_type.value,
                "source": f"{connection.source_cloud}/{connection.source_region}",
                "target": f"{connection.target_cloud}/{connection.target_region}",
                "bandwidth": connection.bandwidth,
                "status": connection.status.value
            })
        
        return matrix
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get connectivity analytics
        
        Returns:
            Connectivity statistics
        """
        total_connections = len(self.connections)
        
        # By status
        by_status = {}
        for connection in self.connections.values():
            status = connection.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By type
        by_type = {}
        for connection in self.connections.values():
            conn_type = connection.connection_type.value
            by_type[conn_type] = by_type.get(conn_type, 0) + 1
        
        # Active connections
        active = len([c for c in self.connections.values() if c.status == ConnectionStatus.CONNECTED])
        
        return {
            "total_connections": total_connections,
            "active_connections": active,
            "by_status": by_status,
            "by_type": by_type
        }