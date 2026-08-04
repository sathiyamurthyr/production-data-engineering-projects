"""
Orchestrator Agent for Enterprise Agentic AI Platform

This module implements the orchestrator that coordinates specialized agents.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field
from .base import BaseAgent, AgentContext, AgentResult
from .registry import AgentRegistry, AgentType

logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Orchestration status"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


class TaskAssignment(BaseModel):
    """Task assignment"""
    task_id: str
    agent_id: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: OrchestrationStatus
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class OrchestratorAgent(BaseAgent):
    """Orchestrator that coordinates the agent ecosystem"""
    
    def __init__(self, config: Dict, registry: AgentRegistry):
        """Initialize orchestrator agent"""
        super().__init__(
            config=config,
            agent_id="orchestrator-agent",
            name="Orchestrator Agent",
            description="Coordinates specialized agents to execute plans",
            capabilities=[
                "orchestration", "task_delegation", "agent_coordination",
                "workflow_execution", "approval_management"
            ]
        )
        self.registry = registry
        self.assignments: Dict[str, TaskAssignment] = {}
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute plan by coordinating agents"""
        logger.info(f"Orchestrator executing: {context.request}")
        
        plan = context.parameters.get("plan")
        if not plan:
            return self.create_result(
                session_id=context.session_id,
                summary="No plan provided for orchestration",
                findings=[{"type": "error", "message": "Missing plan"}],
                confidence=0.5
            )
        
        steps = plan.get("steps", [])
        assignments = []
        
        for step in steps:
            assignment = await self._assign_step(context, step)
            assignments.append(assignment)
        
        return self.create_result(
            session_id=context.session_id,
            summary=f"Orchestrated {len(assignments)} agent tasks",
            findings=[
                {"type": "tasks_assigned", "count": len(assignments)},
                {"type": "orchestration_complete", "assignments": [
                    {"task_id": a.task_id, "agent_id": a.agent_id, "status": a.status.value}
                    for a in assignments
                ]}
            ],
            actions_taken=[
                {"type": "task_assignments", "assignments": [
                    {"task_id": a.task_id, "agent_id": a.agent_id, "action": a.action}
                    for a in assignments
                ]}
            ],
            data={"assignments": [a.model_dump() for a in assignments]},
            confidence=0.9
        )
    
    async def _assign_step(self, context: AgentContext, step: Dict) -> TaskAssignment:
        """Assign a step to the appropriate agent"""
        agent_type_value = step.get("agent_type", "")
        
        # Find agent by type
        matches = []
        if agent_type_value:
            matches = self.registry.find_agents_by_type(
                AgentType(agent_type_value)
            ) if agent_type_value in [t.value for t in AgentType] else []
        
        if not matches:
            # Find by capability
            matches = self.registry.find_agents_by_capability(
                step.get("name", "").lower().replace(" ", "_")
            )
        
        agent_id = matches[0].agent_id if matches else "unknown"
        
        assignment = TaskAssignment(
            task_id=f"task-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(self.assignments)}",
            agent_id=agent_id,
            action=step.get("name", "unknown"),
            parameters=step.get("parameters", {}),
            status=OrchestrationStatus.PENDING
        )
        
        self.assignments[assignment.task_id] = assignment
        
        # Execute agent if available
        instance = self.registry.get_instance(agent_id)
        if instance:
            assignment.status = OrchestrationStatus.EXECUTING
            assignment.started_at = datetime.utcnow()
            
            try:
                agent_context = AgentContext(
                    session_id=context.session_id,
                    user_id=context.user_id,
                    request=f"Execute: {assignment.action}",
                    parameters=assignment.parameters,
                    context_data=context.context_data,
                    parent_agent=self.agent_id
                )
                result = await instance.execute(agent_context)
                assignment.result = result.model_dump()
                assignment.status = OrchestrationStatus.COMPLETED
                assignment.completed_at = datetime.utcnow()
                logger.info(f"Agent task completed: {assignment.task_id} by {agent_id}")
            except Exception as e:
                assignment.status = OrchestrationStatus.FAILED
                assignment.error_message = str(e)
                logger.error(f"Agent execution failed: {assignment.agent_id} - {e}")
        else:
            logger.warning(f"No agent instance found: {agent_id}")
        
        self.execution_history.append(assignment.model_dump())
        return assignment
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get orchestration analytics"""
        total = len(self.assignments)
        by_status = {}
        completed_tasks = 0
        
        for assignment in self.assignments.values():
            status = assignment.status.value
            by_status[status] = by_status.get(status, 0) + 1
            if assignment.status == OrchestrationStatus.COMPLETED:
                completed_tasks += 1
        
        return {
            "total_tasks": total,
            "completed_tasks": completed_tasks,
            "success_rate": (completed_tasks / total * 100) if total > 0 else 0,
            "by_status": by_status
        }