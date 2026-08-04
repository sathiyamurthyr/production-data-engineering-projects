"""
Tool Registry for Enterprise Agentic AI Platform

This module provides tool registration, discovery, and execution.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolPermission(str, Enum):
    """Tool permission levels"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"


class ToolStatus(str, Enum):
    """Tool status"""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class ToolInfo(BaseModel):
    """Tool information"""
    tool_id: str
    name: str
    description: str
    category: str
    permission: ToolPermission
    status: ToolStatus
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    required_roles: List[str] = Field(default_factory=list)
    timeout_seconds: int = 60
    version: str = "1.0.0"
    registered_at: datetime
    updated_at: datetime


class ToolRegistry:
    """
    Enterprise tool registry
    
    This service provides:
    - Tool registration
    - Tool discovery
    - Permission enforcement
    - Tool execution
    """
    
    def __init__(self, config: Dict):
        """Initialize tool registry"""
        self.config = config
        self.tools: Dict[str, ToolInfo] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("Tool Registry initialized")
    
    def register(self, tool_id: str, name: str, description: str, category: str,
                 handler: Callable, permission: ToolPermission = ToolPermission.READ,
                 parameters_schema: Optional[Dict[str, Any]] = None,
                 required_roles: Optional[List[str]] = None,
                 timeout_seconds: int = 60) -> ToolInfo:
        """Register a tool"""
        logger.info(f"Registering tool: {tool_id}")
        
        if tool_id in self.tools:
            raise ValueError(f"Tool already registered: {tool_id}")
        
        info = ToolInfo(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            permission=permission,
            status=ToolStatus.AVAILABLE,
            parameters_schema=parameters_schema or {},
            required_roles=required_roles or ["admin"],
            timeout_seconds=timeout_seconds,
            registered_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.tools[tool_id] = info
        self.tool_handlers[tool_id] = handler
        
        logger.info(f"Tool registered: {tool_id}")
        return info
    
    def get_tool(self, tool_id: str) -> Optional[ToolInfo]:
        """Get tool by ID"""
        return self.tools.get(tool_id)
    
    def list_tools(self, category: Optional[str] = None,
                   permission: Optional[ToolPermission] = None) -> List[ToolInfo]:
        """List tools"""
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if permission:
            tools = [t for t in tools if t.permission == permission]
        
        return tools
    
    def has_permission(self, tool_id: str, role: str) -> bool:
        """Check if role has permission for tool"""
        tool = self.tools.get(tool_id)
        if not tool:
            return False
        
        if "admin" in tool.required_roles:
            return True
        
        return role in tool.required_roles
    
    async def execute(self, tool_id: str, role: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool"""
        tool = self.tools.get(tool_id)
        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_id}"}
        
        if tool.status != ToolStatus.AVAILABLE:
            return {"success": False, "error": f"Tool not available: {tool.status.value}"}
        
        if not self.has_permission(tool_id, role):
            return {"success": False, "error": f"Permission denied for role: {role}"}
        
        handler = self.tool_handlers.get(tool_id)
        if not handler:
            return {"success": False, "error": f"No handler for tool: {tool_id}"}
        
        started = datetime.utcnow()
        
        try:
            result = await handler(**kwargs)
            
            self.execution_history.append({
                "tool_id": tool_id,
                "role": role,
                "status": "success",
                "duration_ms": (datetime.utcnow() - started).total_seconds() * 1000,
                "executed_at": started.isoformat()
            })
            
            return {"success": True, "result": result}
            
        except Exception as e:
            self.execution_history.append({
                "tool_id": tool_id,
                "role": role,
                "status": "failed",
                "error": str(e),
                "executed_at": started.isoformat()
            })
            
            logger.error(f"Tool execution failed: {tool_id} - {e}")
            return {"success": False, "error": str(e)}
    
    def update_status(self, tool_id: str, status: ToolStatus) -> Optional[ToolInfo]:
        """Update tool status"""
        tool = self.tools.get(tool_id)
        if not tool:
            return None
        
        tool.status = status
        tool.updated_at = datetime.utcnow()
        return tool
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get tool analytics"""
        total_tools = len(self.tools)
        
        by_category = {}
        for tool in self.tools.values():
            cat = tool.category
            by_category[cat] = by_category.get(cat, 0) + 1
        
        by_status = {}
        for tool in self.tools.values():
            status = tool.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        total_executions = len(self.execution_history)
        successful = len([e for e in self.execution_history if e["status"] == "success"])
        
        return {
            "total_tools": total_tools,
            "total_executions": total_executions,
            "success_rate": (successful / total_executions * 100) if total_executions > 0 else 0,
            "by_category": by_category,
            "by_status": by_status
        }