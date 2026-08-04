"""
Agent Registry for Enterprise Agentic AI Platform

This module provides agent registration, discovery, and capability management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent types"""
    PLANNER = "planner"
    ORCHESTRATOR = "orchestrator"
    DATA_ENGINEER = "data_engineer"
    PLATFORM_ENGINEER = "platform_engineer"
    SRE = "sre"
    GOVERNANCE = "governance"
    SECURITY = "security"
    ANALYTICS = "analytics"
    REVIEWER = "reviewer"


class AgentStatus(str, Enum):
    """Agent status"""
    REGISTERED = "registered"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DISABLED = "disabled"


class AgentInfo(BaseModel):
    """Agent information"""
    agent_id: str
    name: str
    agent_type: AgentType
    description: str
    capabilities: List[str]
    status: AgentStatus
    version: str
    model: str
    max_concurrent_tasks: int
    supports_tools: bool
    supports_human_in_the_loop: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime
    updated_at: datetime


class AgentRegistry:
    """
    Enterprise agent registry
    
    This service provides:
    - Agent registration
    - Capability discovery
    - Agent status management
    - Agent health monitoring
    """
    
    def __init__(self, config: Dict):
        """
        Initialize agent registry
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_instances: Dict[str, Any] = {}
        
        logger.info("Agent Registry initialized")
    
    def register(self, agent_id: str, agent_type: AgentType, name: str, description: str,
                 capabilities: List[str], version: str = "1.0.0", model: str = "gpt-4",
                 max_concurrent_tasks: int = 5, supports_tools: bool = True,
                 supports_human_in_the_loop: bool = False,
                 metadata: Optional[Dict[str, Any]] = None) -> AgentInfo:
        """
        Register an agent
        
        Args:
            agent_id: Unique agent ID
            agent_type: Agent type
            name: Agent name
            description: Agent description
            capabilities: Agent capabilities
            version: Agent version
            model: LLM model
            max_concurrent_tasks: Max concurrent tasks
            supports_tools: Whether agent supports tools
            supports_human_in_the_loop: Whether agent supports approvals
            metadata: Additional metadata
            
        Returns:
            AgentInfo
        """
        logger.info(f"Registering agent: {agent_id}")
        
        if agent_id in self.agents:
            raise ValueError(f"Agent already registered: {agent_id}")
        
        info = AgentInfo(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            description=description,
            capabilities=capabilities,
            status=AgentStatus.REGISTERED,
            version=version,
            model=model,
            max_concurrent_tasks=max_concurrent_tasks,
            supports_tools=supports_tools,
            supports_human_in_the_loop=supports_human_in_the_loop,
            metadata=metadata or {},
            registered_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.agents[agent_id] = info
        logger.info(f"Agent registered: {agent_id}")
        return info
    
    def register_instance(self, agent_id: str, instance: Any) -> None:
        """Register agent instance"""
        self.agent_instances[agent_id] = instance
        self.agents[agent_id].status = AgentStatus.ACTIVE
        self.agents[agent_id].updated_at = datetime.utcnow()
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_instance(self, agent_id: str) -> Optional[Any]:
        """Get agent instance"""
        return self.agent_instances.get(agent_id)
    
    def find_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """Find agents with specific capability"""
        return [
            agent for agent in self.agents.values()
            if capability in agent.capabilities and agent.status == AgentStatus.ACTIVE
        ]
    
    def find_agents_by_type(self, agent_type: AgentType) -> List[AgentInfo]:
        """Find agents by type"""
        return [
            agent for agent in self.agents.values()
            if agent.agent_type == agent_type
        ]
    
    def list_agents(self, status: Optional[AgentStatus] = None) -> List[AgentInfo]:
        """List agents"""
        agents = list(self.agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        return agents
    
    def update_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentInfo]:
        """Update agent status"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        agent.status = status
        agent.updated_at = datetime.utcnow()
        return agent
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get registry analytics"""
        total = len(self.agents)
        by_type = {}
        by_status = {}
        
        for agent in self.agents.values():
            atype = agent.agent_type.value
            by_type[atype] = by_type.get(atype, 0) + 1
            status = agent.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_agents": total,
            "active_agents": len([a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]),
            "by_type": by_type,
            "by_status": by_status
        }