"""
Planner Agent for Enterprise Agentic AI Platform

This module implements the planner agent that decomposes tasks into actionable plans.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel, Field
from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    """Plan step"""
    step_id: str
    name: str
    description: str
    agent_type: str
    tools: List[str]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    estimated_effort: str = "medium"
    approval_required: bool = False


class ExecutionPlan(BaseModel):
    """Execution plan"""
    plan_id: str
    request: str
    steps: List[PlanStep]
    complexity: str
    estimated_agents: int
    estimated_tools: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlannerAgent(BaseAgent):
    """Planner agent that decomposes complex tasks"""
    
    def __init__(self, config: Dict):
        """Initialize planner agent"""
        super().__init__(
            config=config,
            agent_id="planner-agent",
            name="Planner Agent",
            description="Decomposes complex tasks into actionable multi-agent plans",
            capabilities=[
                "planning", "task_decomposition", "workflow_design",
                "dependency_analysis", "resource_estimation"
            ]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Create execution plan for the request"""
        logger.info(f"Planner executing: {context.request}")
        
        request_type = self._classify_request(context.request, context.parameters)
        plan = self._create_plan(request_type, context.request, context.parameters)
        
        return self.create_result(
            session_id=context.session_id,
            summary=f"Created execution plan with {len(plan.steps)} steps for: {context.request}",
            findings=[
                {"type": "plan_created", "plan_id": plan.plan_id, "complexity": plan.complexity},
                {"type": "request_classification", "request_type": request_type}
            ],
            recommendations=[
                {"type": "agent_allocation", "agents_required": plan.estimated_agents},
                {"type": "tool_requirements", "tools_required": plan.estimated_tools}
            ],
            actions_taken=[
                {"type": "plan_generation", "plan": plan.model_dump()}
            ],
            data={"plan": plan.model_dump()},
            confidence=0.9
        )
    
    def _classify_request(self, request: str, parameters: Dict) -> str:
        """Classify request type"""
        request_lower = request.lower()
        
        if "fail" in request_lower or "error" in request_lower:
            return "failure_assistance"
        elif "cost" in request_lower:
            return "cost_optimization"
        elif "quality" in request_lower:
            return "data_quality"
        elif "schema" in request_lower:
            return "schema_evolution"
        elif "incident" in request_lower or "alert" in request_lower:
            return "incident_assistance"
        elif "document" in request_lower:
            return "documentation"
        elif "optimize" in request_lower:
            return "optimization"
        elif "security" in request_lower:
            return "security_review"
        elif "governance" in request_lower or "compliance" in request_lower:
            return "governance_review"
        else:
            return "general_assistance"
    
    def _create_plan(self, request_type: str, request: str, parameters: Dict) -> ExecutionPlan:
        """Create execution plan based on request type"""
        if request_type == "failure_assistance":
            steps = [
                PlanStep(
                    step_id="step-1", name="Diagnose Failure",
                    description="Investigate pipeline failure",
                    agent_type="sre", tools=["get_pipeline_status", "get_logs"],
                    parameters={"pipeline_id": parameters.get("pipeline_id", "")}
                ),
                PlanStep(
                    step_id="step-2", name="Identify Root Cause",
                    description="Analyze failure logs and identify root cause",
                    agent_type="data_engineer", tools=["analyze_logs", "check_dependencies"],
                    parameters={}, depends_on=["step-1"]
                ),
                PlanStep(
                    step_id="step-3", name="Recommend Fix",
                    description="Provide fix recommendations",
                    agent_type="reviewer", tools=["validate_recommendation"],
                    parameters={}, depends_on=["step-2"],
                    approval_required=True
                )
            ]
        elif request_type == "cost_optimization":
            steps = [
                PlanStep(
                    step_id="step-1", name="Analyze Costs",
                    description="Analyze resource costs",
                    agent_type="platform_engineer", tools=["get_cost_report", "get_resource_usage"],
                    parameters={}
                ),
                PlanStep(
                    step_id="step-2", name="Identify Savings",
                    description="Identify cost saving opportunities",
                    agent_type="analytics", tools=["analyze_usage_patterns"],
                    parameters={}, depends_on=["step-1"]
                ),
                PlanStep(
                    step_id="step-3", name="Recommend Optimizations",
                    description="Provide optimization recommendations",
                    agent_type="reviewer", tools=[],
                    parameters={}, depends_on=["step-2"], approval_required=True
                )
            ]
        else:
            steps = [
                PlanStep(
                    step_id="step-1", name="Gather Context",
                    description="Gather context from enterprise tools",
                    agent_type="platform_engineer", tools=["get_pipeline_status", "get_logs"],
                    parameters={}
                ),
                PlanStep(
                    step_id="step-2", name="Analyze",
                    description="Analyze the situation",
                    agent_type="analytics", tools=["analyze_data"],
                    parameters={}, depends_on=["step-1"]
                ),
                PlanStep(
                    step_id="step-3", name="Recommend",
                    description="Provide recommendation",
                    agent_type="reviewer", tools=[],
                    parameters={}, depends_on=["step-2"]
                )
            ]
        
        return ExecutionPlan(
            plan_id=f"plan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            request=request,
            steps=steps,
            complexity="medium",
            estimated_agents=len(set(s.agent_type for s in steps)),
            estimated_tools=len(set(t for s in steps for t in s.tools))
        )