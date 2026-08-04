"""
Workflow Engine for Cross-Cloud Platform

This module provides workflow orchestration across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow status"""
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(BaseModel):
    """Workflow step"""
    step_id: str
    name: str
    description: str
    action: str
    parameters: Dict[str, Any]
    depends_on: List[str] = Field(default_factory=list)
    timeout: int = 3600
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    on_failure: str = "fail"  # fail, continue, retry


class Workflow(BaseModel):
    """Workflow definition"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus
    cloud: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    created_by: str


class WorkflowInstance(BaseModel):
    """Workflow instance"""
    instance_id: str
    workflow_id: str
    status: WorkflowStatus
    current_step: Optional[str] = None
    step_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WorkflowEngine:
    """
    Cross-cloud workflow engine
    
    This service provides:
    - Workflow definition and management
    - Workflow execution orchestration
    - Step dependency management
    - Error handling and retry
    """
    
    def __init__(self, config: Dict):
        """
        Initialize workflow engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.workflows: Dict[str, Workflow] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self.step_handlers: Dict[str, Callable] = {}
        
        logger.info("Workflow Engine initialized")
    
    def register_step_handler(self, action: str, handler: Callable) -> None:
        """
        Register step handler
        
        Args:
            action: Action name
            handler: Handler function
        """
        self.step_handlers[action] = handler
        logger.info(f"Step handler registered for action: {action}")
    
    async def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        cloud: str,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: str = "system"
    ) -> Workflow:
        """
        Create workflow
        
        Args:
            workflow_id: Workflow ID
            name: Workflow name
            description: Workflow description
            steps: Workflow steps
            cloud: Cloud provider
            variables: Workflow variables
            metadata: Additional metadata
            created_by: Creator
            
        Returns:
            Workflow
        """
        logger.info(f"Creating workflow: {workflow_id}")
        
        if workflow_id in self.workflows:
            raise ValueError(f"Workflow already exists: {workflow_id}")
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            status=WorkflowStatus.DRAFT,
            cloud=cloud,
            variables=variables or {},
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by
        )
        
        self.workflows[workflow_id] = workflow
        
        logger.info(f"Workflow created: {workflow_id}")
        return workflow
    
    async def activate_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Activate workflow
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Updated workflow
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow not found: {workflow_id}")
            return None
        
        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = datetime.utcnow()
        
        logger.info(f"Workflow activated: {workflow_id}")
        return workflow
    
    async def execute_workflow(
        self,
        workflow_id: str,
        instance_variables: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowInstance]:
        """
        Execute workflow
        
        Args:
            workflow_id: Workflow ID
            instance_variables: Instance variables
            
        Returns:
            Workflow instance
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow not found: {workflow_id}")
            return None
        
        if workflow.status != WorkflowStatus.ACTIVE:
            logger.warning(f"Workflow not active: {workflow_id}")
            return None
        
        logger.info(f"Executing workflow: {workflow_id}")
        
        # Create instance
        instance_id = f"instance-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        instance = WorkflowInstance(
            instance_id=instance_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            variables={**workflow.variables, **(instance_variables or {})},
            started_at=datetime.utcnow()
        )
        
        self.instances[instance_id] = instance
        
        # Execute steps
        try:
            await self._execute_steps(workflow, instance)
            
            # Update instance status
            if instance.status == WorkflowStatus.RUNNING:
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.utcnow()
                
                logger.info(f"Workflow completed: {workflow_id} (instance: {instance_id})")
            
        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.error_message = str(e)
            logger.error(f"Workflow failed: {workflow_id} - {e}")
        
        return instance
    
    async def _execute_steps(self, workflow: Workflow, instance: WorkflowInstance) -> None:
        """
        Execute workflow steps
        
        Args:
            workflow: Workflow
            instance: Workflow instance
        """
        completed_steps = set()
        
        for step in workflow.steps:
            # Check dependencies
            if not all(dep in completed_steps for dep in step.depends_on):
                logger.warning(f"Step dependencies not met: {step.step_id}")
                continue
            
            # Update current step
            instance.current_step = step.step_id
            
            # Execute step
            try:
                handler = self.step_handlers.get(step.action)
                if not handler:
                    raise ValueError(f"No handler for action: {step.action}")
                
                result = await handler(step.parameters, instance.variables)
                
                # Store result
                instance.step_results[step.step_id] = result
                completed_steps.add(step.step_id)
                
                logger.info(f"Step completed: {step.step_id}")
                
            except Exception as e:
                logger.error(f"Step failed: {step.step_id} - {e}")
                
                # Handle failure
                if step.on_failure == "fail":
                    instance.status = WorkflowStatus.FAILED
                    instance.error_message = f"Step {step.step_id} failed: {str(e)}"
                    raise
                elif step.on_failure == "continue":
                    logger.warning(f"Continuing despite step failure: {step.step_id}")
                    continue
                elif step.on_failure == "retry":
                    # Implement retry logic
                    logger.info(f"Retrying step: {step.step_id}")
                    # For simplicity, just continue
                    continue
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Get workflow by ID
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow if found, None otherwise
        """
        return self.workflows.get(workflow_id)
    
    async def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """
        Get workflow instance by ID
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Workflow instance if found, None otherwise
        """
        return self.instances.get(instance_id)
    
    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        cloud: Optional[str] = None
    ) -> List[Workflow]:
        """
        List workflows
        
        Args:
            status: Workflow status filter
            cloud: Cloud provider filter
            
        Returns:
            List of workflows
        """
        workflows = list(self.workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        if cloud:
            workflows = [w for w in workflows if w.cloud == cloud]
        
        return workflows
    
    async def list_instances(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowInstance]:
        """
        List workflow instances
        
        Args:
            workflow_id: Workflow ID filter
            status: Workflow status filter
            
        Returns:
            List of workflow instances
        """
        instances = list(self.instances.values())
        
        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]
        
        if status:
            instances = [i for i in instances if i.status == status]
        
        # Sort by started_at desc
        instances.sort(key=lambda i: i.started_at or datetime.utcnow(), reverse=True)
        
        return instances
    
    async def cancel_workflow(self, instance_id: str) -> Optional[WorkflowInstance]:
        """
        Cancel workflow instance
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Updated workflow instance
        """
        instance = self.instances.get(instance_id)
        if not instance:
            logger.warning(f"Workflow instance not found: {instance_id}")
            return None
        
        if instance.status == WorkflowStatus.RUNNING:
            instance.status = WorkflowStatus.CANCELLED
            logger.info(f"Workflow instance cancelled: {instance_id}")
        
        return instance