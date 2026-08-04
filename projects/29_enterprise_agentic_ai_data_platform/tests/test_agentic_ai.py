"""
Comprehensive tests for Enterprise Agentic AI for Data Engineering

This test suite covers:
- Agent registry
- Planner agent
- Orchestrator agent
- Specialized agents
- Tool registry
- Enterprise memory
- Knowledge base
- AI Gateway
"""

import pytest
import asyncio
from datetime import datetime

# Agent system
from agents.registry import AgentRegistry, AgentType, AgentStatus
from agents.base import BaseAgent, AgentContext, AgentResult
from agents.planner import PlannerAgent
from agents.orchestrator import OrchestratorAgent
from agents.specialized import (
    DataEngineerAgent, PlatformEngineerAgent, SREAgent,
    GovernanceAgent, SecurityAgent, AnalyticsAgent, ReviewerAgent
)

# Tools
from tools.registry import ToolRegistry, ToolPermission, ToolStatus

# Memory & Knowledge
from memory.enterprise_memory import EnterpriseMemory
from knowledge.knowledge_base import KnowledgeBase

# API Gateway
from apis.gateway import AIGateway, RequestStatus


def async_test(coro):
    """Helper to run async tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


# ──────────────────────────────────────────────
# Agent Registry Tests
# ──────────────────────────────────────────────

class TestAgentRegistry:
    """Tests for agent registry"""

    def setup_method(self):
        self.registry = AgentRegistry({})

    def test_register_agent(self):
        """Test agent registration"""
        info = self.registry.register(
            agent_id="test-agent",
            agent_type=AgentType.DATA_ENGINEER,
            name="Test Agent",
            description="Test agent",
            capabilities=["pipeline_analysis"]
        )
        assert info.agent_id == "test-agent"
        assert info.status == AgentStatus.REGISTERED

    def test_find_by_capability(self):
        """Test capability discovery"""
        self.registry.register(
            agent_id="agent-1",
            agent_type=AgentType.SRE,
            name="SRE Agent",
            description="SRE",
            capabilities=["incident_response"]
        )
        self.registry.update_status("agent-1", AgentStatus.ACTIVE)
        
        matches = self.registry.find_agents_by_capability("incident_response")
        assert len(matches) >= 1

    def test_analytics(self):
        """Test registry analytics"""
        self.registry.register(
            agent_id="agent-2",
            agent_type=AgentType.PLANNER,
            name="Planner",
            description="Planner",
            capabilities=["planning"]
        )
        analytics = self.registry.get_analytics()
        assert analytics["total_agents"] >= 1


# ──────────────────────────────────────────────
# Planner Agent Tests
# ──────────────────────────────────────────────

class TestPlannerAgent:
    """Tests for planner agent"""

    def setup_method(self):
        self.planner = PlannerAgent({})

    def test_plan_creation(self):
        """Test plan creation"""
        context = AgentContext(
            session_id="sess-1",
            user_id="user-1",
            request="Investigate why pipeline sales_daily failed",
            parameters={"pipeline_id": "sales_daily"}
        )
        result = async_test(self.planner.execute(context))
        assert result is not None
        assert "plan" in result.data
        assert len(result.data["plan"]["steps"]) >= 1

    def test_request_classification(self):
        """Test request classification"""
        context = AgentContext(
            session_id="sess-2",
            user_id="user-1",
            request="Optimize infrastructure costs",
            parameters={}
        )
        result = async_test(self.planner.execute(context))
        assert result is not None
        assert result.data["plan"]["request"] == "Optimize infrastructure costs"


# ──────────────────────────────────────────────
# Specialized Agent Tests
# ──────────────────────────────────────────────

class TestSpecializedAgents:
    """Tests for specialized agents"""

    def setup_method(self):
        self.data_engineer = DataEngineerAgent({})
        self.platform_engineer = PlatformEngineerAgent({})
        self.sre = SREAgent({})
        self.governance = GovernanceAgent({})
        self.security = SecurityAgent({})
        self.analytics = AnalyticsAgent({})
        self.reviewer = ReviewerAgent({})

    def test_data_engineer(self):
        """Test data engineer agent"""
        context = AgentContext(
            session_id="sess-1",
            user_id="user-1",
            request="Analyze pipeline",
            parameters={"pipeline_id": "sales_daily"}
        )
        result = async_test(self.data_engineer.execute(context))
        assert result is not None
        assert len(result.findings) >= 1

    def test_platform_engineer(self):
        """Test platform engineer agent"""
        context = AgentContext(
            session_id="sess-2",
            user_id="user-1",
            request="Assess infrastructure",
            parameters={"resource_id": "cluster-1"}
        )
        result = async_test(self.platform_engineer.execute(context))
        assert result is not None
        assert len(result.recommendations) >= 1

    def test_sre_agent(self):
        """Test SRE agent"""
        context = AgentContext(
            session_id="sess-3",
            user_id="user-1",
            request="Investigate incident",
            parameters={"incident_id": "INC-001", "severity": "P2"}
        )
        result = async_test(self.sre.execute(context))
        assert result is not None
        assert len(result.findings) >= 1

    def test_governance_agent(self):
        """Test governance agent"""
        context = AgentContext(
            session_id="sess-4",
            user_id="user-1",
            request="Review compliance",
            parameters={"resource": "customer-data"}
        )
        result = async_test(self.governance.execute(context))
        assert result is not None
        assert result.approval_required is True

    def test_security_agent(self):
        """Test security agent"""
        context = AgentContext(
            session_id="sess-5",
            user_id="user-1",
            request="Security assessment",
            parameters={"target": "data-platform"}
        )
        result = async_test(self.security.execute(context))
        assert result is not None
        assert result.data["security_score"] == 82

    def test_analytics_agent(self):
        """Test analytics agent"""
        context = AgentContext(
            session_id="sess-6",
            user_id="user-1",
            request="Analyze trends",
            parameters={"metric": "pipeline_success_rate"}
        )
        result = async_test(self.analytics.execute(context))
        assert result is not None
        assert len(result.findings) >= 1

    def test_reviewer_agent(self):
        """Test reviewer agent"""
        context = AgentContext(
            session_id="sess-7",
            user_id="user-1",
            request="Review output",
            parameters={"review_target": "agent_output"}
        )
        result = async_test(self.reviewer.execute(context))
        assert result is not None
        assert result.data["quality_score"] == 0.88


# ──────────────────────────────────────────────
# Tool Registry Tests
# ──────────────────────────────────────────────

class TestToolRegistry:
    """Tests for tool registry"""

    def setup_method(self):
        self.registry = ToolRegistry({})

    def test_register_and_execute(self):
        """Test tool registration and execution"""
        async def handler(**kwargs):
            return {"status": "ok", "data": kwargs}

        self.registry.register(
            tool_id="test-tool",
            name="Test Tool",
            description="Test tool",
            category="test",
            handler=handler,
            permission=ToolPermission.READ,
            required_roles=["admin"]
        )
        
        result = async_test(self.registry.execute("test-tool", "admin", key="value"))
        assert result["success"] is True
        assert result["result"]["status"] == "ok"

    def test_permission_denied(self):
        """Test permission enforcement"""
        async def handler(**kwargs):
            return {"status": "ok"}

        self.registry.register(
            tool_id="restricted-tool",
            name="Restricted",
            description="Restricted tool",
            category="test",
            handler=handler,
            required_roles=["admin"]
        )
        
        result = async_test(self.registry.execute("restricted-tool", "user", key="value"))
        assert result["success"] is False
        assert "Permission denied" in result["error"]


# ──────────────────────────────────────────────
# Memory & Knowledge Tests
# ──────────────────────────────────────────────

class TestMemoryAndKnowledge:
    """Tests for memory and knowledge systems"""

    def setup_method(self):
        self.memory = EnterpriseMemory({})
        self.knowledge = KnowledgeBase({})

    def test_memory_store_retrieve(self):
        """Test memory storage and retrieval"""
        async_test(self.memory.store(
            agent_id="agent-1",
            session_id="sess-1",
            memory_type="fact",
            content="Pipeline sales_daily uses incremental loading",
            importance=0.8
        ))
        memories = async_test(self.memory.retrieve(agent_id="agent-1"))
        assert len(memories) >= 1

    def test_memory_recall(self):
        """Test memory recall"""
        async_test(self.memory.store(
            agent_id="agent-1",
            session_id="sess-1",
            memory_type="learning",
            content="Schema drift caused pipeline failure",
            importance=0.9
        ))
        results = async_test(self.memory.recall("agent-1", "schema drift"))
        assert len(results) >= 1

    def test_knowledge_base(self):
        """Test knowledge base"""
        async_test(self.knowledge.add_document(
            title="Pipeline Troubleshooting Guide",
            content="Common pipeline failures and solutions",
            category="troubleshooting",
            tags=["pipeline", "failure"]
        ))
        results = async_test(self.knowledge.search("pipeline failure"))
        assert len(results) >= 1


# ──────────────────────────────────────────────
# AI Gateway Tests
# ──────────────────────────────────────────────

class TestAIGateway:
    """Tests for AI Gateway"""

    def setup_method(self):
        self.planner = PlannerAgent({})
        self.registry = AgentRegistry({})
        self.orchestrator = OrchestratorAgent({}, self.registry)
        self.gateway = AIGateway({}, planner=self.planner, orchestrator=self.orchestrator)

    def test_submit_request(self):
        """Test request submission"""
        request = async_test(self.gateway.submit_request(
            user_id="user-1",
            request="Investigate pipeline failure",
            parameters={"pipeline_id": "sales_daily"}
        ))
        assert request is not None
        assert request.request_id is not None

    def test_gateway_analytics(self):
        """Test gateway analytics"""
        async_test(self.gateway.submit_request(
            user_id="user-1",
            request="Optimize costs"
        ))
        analytics = async_test(self.gateway.get_analytics())
        assert analytics["total_requests"] >= 1


# ──────────────────────────────────────────────
# End-to-End Platform Test
# ──────────────────────────────────────────────

class TestEndToEnd:
    """End-to-end platform test"""

    def test_complete_workflow(self):
        """Test complete agentic AI workflow"""
        # 1. Initialize registry
        registry = AgentRegistry({})
        
        # 2. Register all agents
        agents = [
            (PlannerAgent({}), AgentType.PLANNER, "planner-agent", ["planning"]),
            (DataEngineerAgent({}), AgentType.DATA_ENGINEER, "data-engineer-agent", ["pipeline_analysis"]),
            (PlatformEngineerAgent({}), AgentType.PLATFORM_ENGINEER, "platform-engineer-agent", ["infrastructure_analysis"]),
            (SREAgent({}), AgentType.SRE, "sre-agent", ["incident_response"]),
            (GovernanceAgent({}), AgentType.GOVERNANCE, "governance-agent", ["policy_compliance"]),
            (SecurityAgent({}), AgentType.SECURITY, "security-agent", ["security_assessment"]),
            (AnalyticsAgent({}), AgentType.ANALYTICS, "analytics-agent", ["data_analysis"]),
            (ReviewerAgent({}), AgentType.REVIEWER, "reviewer-agent", ["output_review"])
        ]
        
        for agent, agent_type, agent_id, capabilities in agents:
            registry.register(
                agent_id=agent_id,
                agent_type=agent_type,
                name=agent_id,
                description=f"{agent_id} description",
                capabilities=capabilities
            )
            registry.register_instance(agent_id, agent)
        
        # 3. Create orchestrator
        orchestrator = OrchestratorAgent({}, registry)
        
        # 4. Create gateway
        planner = PlannerAgent({})
        gateway = AIGateway({}, planner=planner, orchestrator=orchestrator)
        
        # 5. Submit request
        request = async_test(gateway.submit_request(
            user_id="data-engineer-1",
            request="Investigate why pipeline sales_daily failed",
            parameters={"pipeline_id": "sales_daily"}
        ))
        
        assert request is not None
        assert request.status in [RequestStatus.COMPLETED, RequestStatus.FAILED]
        
        # 6. Verify analytics
        analytics = async_test(gateway.get_analytics())
        assert analytics["total_requests"] >= 1