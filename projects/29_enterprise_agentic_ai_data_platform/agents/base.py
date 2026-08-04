"""
Base Agent for Enterprise Agentic AI Platform

This module provides the base agent interface and common functionality.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentTone(str, Enum):
    """Agent response tones"""
    ANALYTICAL = "analytical"
    CONCISE = "concise"
    DETAILED = "detailed"
    DIPLOMATIC = "diplomatic"


class AgentContext(BaseModel):
    """Agent execution context"""
    session_id: str
    user_id: str
    request: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    parent_agent: Optional[str] = None
    child_agents: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Agent execution result"""
    agent_id: str
    session_id: str
    summary: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    approval_required: bool = False
    approval_reason: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    """
    Base agent class
    
    This class provides:
    - Agent context management
    - Tool execution
    - Result formatting
    - Error handling
    """
    
    def __init__(self, config: Dict, agent_id: str, name: str, description: str,
                 capabilities: List[str]):
        """
        Initialize base agent
        
        Args:
            config: Configuration dictionary
            agent_id: Agent ID
            name: Agent name
            description: Agent description
            capabilities: Agent capabilities
        """
        self.config = config
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.tools: Dict[str, Callable] = {}
        self.memory: Dict[str, Any] = {}
        
        logger.info(f"Agent initialized: {agent_id} ({name})")
    
    def register_tool(self, tool_name: str, tool_func: Callable) -> None:
        """Register a tool with the agent"""
        self.tools[tool_name] = tool_func
        logger.info(f"Tool registered: {tool_name} for agent {self.agent_id}")
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
        return await self.tools[tool_name](**kwargs)
    
    def store_memory(self, key: str, value: Any) -> None:
        """Store value in agent memory"""
        self.memory[key] = value
    
    def retrieve_memory(self, key: str, default: Any = None) -> Any:
        """Retrieve value from agent memory"""
        return self.memory.get(key, default)
    
    def create_context(self, session_id: str, user_id: str, request: str,
                       parameters: Optional[Dict[str, Any]] = None,
                       context_data: Optional[Dict[str, Any]] = None) -> AgentContext:
        """Create agent context"""
        return AgentContext(
            session_id=session_id,
            user_id=user_id,
            request=request,
            parameters=parameters or {},
            context_data=context_data or {}
        )
    
    def create_result(self, session_id: str, summary: str,
                      findings: Optional[List[Dict[str, Any]]] = None,
                      recommendations: Optional[List[Dict[str, Any]]] = None,
                      actions_taken: Optional[List[Dict[str, Any]]] = None,
                      approval_required: bool = False,
                      approval_reason: Optional[str] = None,
                      data: Optional[Dict[str, Any]] = None,
                      confidence: float = 1.0) -> AgentResult:
        """Create agent result"""
        return AgentResult(
            agent_id=self.agent_id,
            session_id=session_id,
            summary=summary,
            findings=findings or [],
            recommendations=recommendations or [],
            actions_taken=actions_taken or [],
            approval_required=approval_required,
            approval_reason=approval_reason,
            data=data or {},
            confidence=confidence
        )
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's primary function"""
        pass