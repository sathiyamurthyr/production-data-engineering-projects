"""
AI Gateway for Enterprise Agentic AI Platform

This module provides the AI Gateway that routes requests to the agent platform.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RequestStatus(str, Enum):
    """Request status"""
    RECEIVED = "received"
    PLANNING = "planning"
    ORCHESTRATING = "orchestrating"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class GatewayRequest(BaseModel):
    """Gateway request"""
    request_id: str
    user_id: str
    request: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: RequestStatus
    session_id: str
    agent_chain: List[str] = Field(default_factory=list)
    response: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class AIGateway:
    """
    AI Gateway for routing requests
    
    This service provides:
    - Request routing
    - Session management
    - Agent chain tracking
    - Response aggregation
    """
    
    def __init__(self, config: Dict, agent_registry=None, orchestrator=None,
                 planner=None, memory=None, knowledge_base=None):
        """Initialize AI Gateway"""
        self.config = config
        self.agent_registry = agent_registry
        self.orchestrator = orchestrator
        self.planner = planner
        self.memory = memory
        self.knowledge_base = knowledge_base
        self.requests: Dict[str, GatewayRequest] = {}
        
        logger.info("AI Gateway initialized")
    
    async def submit_request(self, user_id: str, request: str,
                             parameters: Optional[Dict[str, Any]] = None) -> GatewayRequest:
        """Submit a request to the platform"""
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        
        gateway_request = GatewayRequest(
            request_id=request_id,
            user_id=user_id,
            request=request,
            parameters=parameters or {},
            status=RequestStatus.RECEIVED,
            session_id=session_id,
            created_at=datetime.utcnow()
        )
        
        self.requests[request_id] = gateway_request
        logger.info(f"Request received: {request_id}")
        
        # Process asynchronously in real implementation
        response = await self._process(request_id)
        return gateway_request
    
    async def _process(self, request_id: str) -> GatewayRequest:
        """Process a request through the agent chain"""
        gateway_request = self.requests[request_id]
        
        # 1. Planning phase
        gateway_request.status = RequestStatus.PLANNING
        gateway_request.agent_chain.append("planner-agent")
        
        plan = None
        if self.planner:
            from agents.base import AgentContext
            context = AgentContext(
                session_id=gateway_request.session_id,
                user_id=gateway_request.user_id,
                request=gateway_request.request,
                parameters=gateway_request.parameters
            )
            plan_result = await self.planner.execute(context)
            plan = plan_result.data.get("plan")
        
        # 2. Orchestration phase
        if plan:
            gateway_request.status = RequestStatus.ORCHESTRATING
            
            if self.orchestrator:
                from agents.base import AgentContext
                context = AgentContext(
                    session_id=gateway_request.session_id,
                    user_id=gateway_request.user_id,
                    request=gateway_request.request,
                    parameters={"plan": plan}
                )
                orchestration_result = await self.orchestrator.execute(context)
                
                gateway_request.agent_chain.extend(
                    a.get("agent_id", "") for a in orchestration_result.data.get("assignments", [])
                )
                
                gateway_request.status = RequestStatus.COMPLETED
                gateway_request.response = orchestration_result.model_dump()
                gateway_request.completed_at = datetime.utcnow()
            else:
                gateway_request.status = RequestStatus.COMPLETED
                gateway_request.response = {"plan": plan}
                gateway_request.completed_at = datetime.utcnow()
        else:
            gateway_request.status = RequestStatus.FAILED
            gateway_request.response = {"error": "Planning failed"}
        
        logger.info(f"Request completed: {request_id}")
        return gateway_request
    
    async def get_request(self, request_id: str) -> Optional[GatewayRequest]:
        """Get request by ID"""
        return self.requests.get(request_id)
    
    async def list_requests(self, user_id: Optional[str] = None,
                            status: Optional[RequestStatus] = None) -> List[GatewayRequest]:
        """List requests"""
        requests = list(self.requests.values())
        
        if user_id:
            requests = [r for r in requests if r.user_id == user_id]
        if status:
            requests = [r for r in requests if r.status == status]
        
        requests.sort(key=lambda r: r.created_at, reverse=True)
        return requests
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get gateway analytics"""
        total = len(self.requests)
        
        by_status = {}
        for req in self.requests.values():
            status = req.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        by_user = {}
        for req in self.requests.values():
            user = req.user_id
            by_user[user] = by_user.get(user, 0) + 1
        
        return {
            "total_requests": total,
            "by_status": by_status,
            "by_user": by_user,
            "avg_agent_chain_length": sum(len(r.agent_chain) for r in self.requests.values()) / total if total > 0 else 0
        }