"""
Data Lineage Tracker for Cross-Cloud Data Management

This module provides data lineage tracking across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TransformationType(str, Enum):
    """Transformation types"""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    SPLIT = "split"
    MERGE = "merge"
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"


@dataclass
class LineageNode:
    """Lineage node"""
    node_id: str
    resource_id: str
    resource_type: str
    cloud: str
    region: str
    transformation: Optional[TransformationType] = None
    transformation_details: Optional[Dict[str, Any]] = None


@dataclass
class LineageEdge:
    """Lineage edge"""
    source_id: str
    target_id: str
    transformation: TransformationType
    timestamp: datetime
    metadata: Dict[str, Any]


class DataLineageTracker:
    """
    Cross-cloud data lineage tracker
    
    This service provides:
    - Data lineage tracking
    - Impact analysis
    - Root cause analysis
    - Data flow visualization
    """
    
    def __init__(self, config: Dict):
        """
        Initialize data lineage tracker
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[LineageEdge] = []
        
        logger.info("Data Lineage Tracker initialized")
    
    async def add_node(
        self,
        node_id: str,
        resource_id: str,
        resource_type: str,
        cloud: str,
        region: str,
        transformation: Optional[TransformationType] = None,
        transformation_details: Optional[Dict[str, Any]] = None
    ) -> LineageNode:
        """
        Add lineage node
        
        Args:
            node_id: Node ID
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            region: Cloud region
            transformation: Transformation type
            transformation_details: Transformation details
            
        Returns:
            Lineage node
        """
        logger.info(f"Adding lineage node: {node_id}")
        
        node = LineageNode(
            node_id=node_id,
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud,
            region=region,
            transformation=transformation,
            transformation_details=transformation_details
        )
        
        self.nodes[node_id] = node
        
        logger.info(f"Lineage node added: {node_id}")
        return node
    
    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        transformation: TransformationType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LineageEdge:
        """
        Add lineage edge
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            transformation: Transformation type
            metadata: Additional metadata
            
        Returns:
            Lineage edge
        """
        logger.info(f"Adding lineage edge: {source_id} -> {target_id}")
        
        # Verify nodes exist
        if source_id not in self.nodes:
            raise ValueError(f"Source node not found: {source_id}")
        
        if target_id not in self.nodes:
            raise ValueError(f"Target node not found: {target_id}")
        
        # Create edge
        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            transformation=transformation,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.edges.append(edge)
        
        logger.info(f"Lineage edge added: {source_id} -> {target_id}")
        return edge
    
    async def get_lineage(
        self,
        resource_id: str,
        direction: str = "both",
        depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get lineage for resource
        
        Args:
            resource_id: Resource ID
            direction: Direction (upstream, downstream, both)
            depth: Maximum depth
            
        Returns:
            Lineage graph
        """
        # Find node for resource
        start_node = None
        for node in self.nodes.values():
            if node.resource_id == resource_id:
                start_node = node
                break
        
        if not start_node:
            return {"nodes": [], "edges": []}
        
        # Build lineage graph
        graph = {
            "nodes": [],
            "edges": []
        }
        
        visited = set()
        
        if direction in ["upstream", "both"]:
            await self._build_upstream_lineage(start_node.node_id, graph, visited, depth)
        
        if direction in ["downstream", "both"]:
            await self._build_downstream_lineage(start_node.node_id, graph, visited, depth)
        
        return graph
    
    async def _build_upstream_lineage(
        self,
        node_id: str,
        graph: Dict[str, Any],
        visited: set,
        depth: int,
        current_depth: int = 0
    ) -> None:
        """
        Build upstream lineage
        
        Args:
            node_id: Node ID
            graph: Graph to build
            visited: Visited nodes
            depth: Maximum depth
            current_depth: Current depth
        """
        if current_depth >= depth or node_id in visited:
            return
        
        visited.add(node_id)
        
        # Add node
        node = self.nodes.get(node_id)
        if node:
            graph["nodes"].append({
                "node_id": node.node_id,
                "resource_id": node.resource_id,
                "resource_type": node.resource_type,
                "cloud": node.cloud,
                "transformation": node.transformation.value if node.transformation else None
            })
        
        # Find upstream edges
        for edge in self.edges:
            if edge.target_id == node_id:
                # Add edge
                graph["edges"].append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "transformation": edge.transformation.value,
                    "timestamp": edge.timestamp.isoformat()
                })
                
                # Recurse
                await self._build_upstream_lineage(
                    edge.source_id,
                    graph,
                    visited,
                    depth,
                    current_depth + 1
                )
    
    async def _build_downstream_lineage(
        self,
        node_id: str,
        graph: Dict[str, Any],
        visited: set,
        depth: int,
        current_depth: int = 0
    ) -> None:
        """
        Build downstream lineage
        
        Args:
            node_id: Node ID
            graph: Graph to build
            visited: Visited nodes
            depth: Maximum depth
            current_depth: Current depth
        """
        if current_depth >= depth or node_id in visited:
            return
        
        visited.add(node_id)
        
        # Add node
        node = self.nodes.get(node_id)
        if node:
            graph["nodes"].append({
                "node_id": node.node_id,
                "resource_id": node.resource_id,
                "resource_type": node.resource_type,
                "cloud": node.cloud,
                "transformation": node.transformation.value if node.transformation else None
            })
        
        # Find downstream edges
        for edge in self.edges:
            if edge.source_id == node_id:
                # Add edge
                graph["edges"].append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "transformation": edge.transformation.value,
                    "timestamp": edge.timestamp.isoformat()
                })
                
                # Recurse
                await self._build_downstream_lineage(
                    edge.target_id,
                    graph,
                    visited,
                    depth,
                    current_depth + 1
                )
    
    async def get_upstream_resources(
        self,
        resource_id: str,
        depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get upstream resources
        
        Args:
            resource_id: Resource ID
            depth: Maximum depth
            
        Returns:
            List of upstream resources
        """
        lineage = await self.get_lineage(resource_id, direction="upstream", depth=depth)
        return lineage["nodes"]
    
    async def get_downstream_resources(
        self,
        resource_id: str,
        depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get downstream resources
        
        Args:
            resource_id: Resource ID
            depth: Maximum depth
            
        Returns:
            List of downstream resources
        """
        lineage = await self.get_lineage(resource_id, direction="downstream", depth=depth)
        return lineage["nodes"]
    
    async def get_impact_analysis(
        self,
        resource_id: str
    ) -> Dict[str, Any]:
        """
        Get impact analysis for resource
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Impact analysis
        """
        # Get downstream resources
        downstream = await self.get_downstream_resources(resource_id, depth=10)
        
        # Group by cloud
        by_cloud = {}
        for node in downstream:
            cloud = node["cloud"]
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # Group by resource type
        by_type = {}
        for node in downstream:
            resource_type = node["resource_type"]
            by_type[resource_type] = by_type.get(resource_type, 0) + 1
        
        return {
            "resource_id": resource_id,
            "downstream_count": len(downstream),
            "by_cloud": by_cloud,
            "by_resource_type": by_type,
            "affected_resources": downstream
        }
    
    async def get_root_cause(
        self,
        resource_id: str
    ) -> Dict[str, Any]:
        """
        Get root cause analysis for resource
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Root cause analysis
        """
        # Get upstream resources
        upstream = await self.get_upstream_resources(resource_id, depth=10)
        
        # Find source resources (no upstream)
        sources = []
        for node in upstream:
            # Check if node has upstream
            has_upstream = False
            for edge in self.edges:
                if edge.target_id == node["node_id"]:
                    has_upstream = True
                    break
            
            if not has_upstream:
                sources.append(node)
        
        return {
            "resource_id": resource_id,
            "upstream_count": len(upstream),
            "source_count": len(sources),
            "sources": sources,
            "upstream_resources": upstream
        }
    
    async def get_lineage_analytics(self) -> Dict[str, Any]:
        """
        Get lineage analytics
        
        Returns:
            Lineage statistics
        """
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        
        # By cloud
        by_cloud = {}
        for node in self.nodes.values():
            cloud = node.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By transformation
        by_transformation = {}
        for edge in self.edges:
            transformation = edge.transformation.value
            by_transformation[transformation] = by_transformation.get(transformation, 0) + 1
        
        # By resource type
        by_resource_type = {}
        for node in self.nodes.values():
            resource_type = node.resource_type
            by_resource_type[resource_type] = by_resource_type.get(resource_type, 0) + 1
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "by_cloud": by_cloud,
            "by_transformation": by_transformation,
            "by_resource_type": by_resource_type
        }