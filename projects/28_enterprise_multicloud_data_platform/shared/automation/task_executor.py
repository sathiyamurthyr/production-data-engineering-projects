"""
Task Executor for Cross-Cloud Platform

This module provides task execution capabilities across Azure and AWS.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution modes"""
    SYNC = "sync"
    ASYNC = "async"
    BATCH = "batch"
    STREAMING = "streaming"


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TaskDefinition(BaseModel):
    """Task definition"""
    task_id: str
    name: str
    description: str
    action: str
    parameters: Dict[str, Any]
    execution_mode: ExecutionMode
    timeout: int = 3600
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    cloud: str
    resource_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskExecution(BaseModel):
    """Task execution"""
    execution_id: str
    task_id: str
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None


class TaskExecutor:
    """
    Cross-cloud task executor
    
    This service provides:
    - Task execution
    - Execution mode management
    - Retry and timeout handling
    - Execution tracking
    """
    
    def __init__(self, config: Dict):
        """
        Initialize task executor
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.task_definitions: Dict[str, TaskDefinition] = {}
        self.executions: Dict[str, TaskExecution] = {}
        self.execution_handlers: Dict[str, Callable] = {}
        self.max_concurrent_executions = config.get("max_concurrent_executions", 20)
        self.running_executions = 0
        
        logger.info("Task Executor initialized")
    
    def register_handler(self, action: str, handler: Callable) -> None:
        """
        Register execution handler
        
        Args:
            action: Action name
            handler: Handler function
        """
        self.execution_handlers[action] = handler
        logger.info(f"Handler registered for action: {action}")
    
    async def define_task(self, task: TaskDefinition) -> TaskDefinition:
        """
        Define task
        
        Args:
            task: Task definition
            
        Returns:
            Task definition
        """
        logger.info(f"Defining task: {task.task_id}")
        
        if task.task_id in self.task_definitions:
            raise ValueError(f"Task already defined: {task.task_id}")
        
        self.task_definitions[task.task_id] = task
        
        logger.info(f"Task defined: {task.task_id}")
        return task
    
    async def execute_task(
        self,
        task_id: str,
        execution_params: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskExecution]:
        """
        Execute task
        
        Args:
            task_id: Task ID
            execution_params: Execution parameters
            
        Returns:
            Task execution
        """
        task = self.task_definitions.get(task_id)
        if not task:
            logger.warning(f"Task not defined: {task_id}")
            return None
        
        logger.info(f"Executing task: {task_id}")
        
        # Create execution
        execution_id = f"exec-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            status=ExecutionStatus.QUEUED,
            max_attempts=task.retry_policy.get("max_attempts", 3)
        )
        
        self.executions[execution_id] = execution
        self.running_executions += 1
        
        try:
            # Update status
            execution.status = ExecutionStatus.EXECUTING
            execution.started_at = datetime.utcnow()
            
            # Merge parameters
            params = {**task.parameters, **(execution_params or {})}
            
            # Get handler
            handler = self.execution_handlers.get(task.action)
            if not handler:
                raise ValueError(f"No handler for action: {task.action}")
            
            # Execute based on mode
            if task.execution_mode == ExecutionMode.SYNC:
                result = await self._execute_sync(handler, params, task.timeout)
            elif task.execution_mode == ExecutionMode.ASYNC:
                result = await self._execute_async(handler, params, task.timeout)
            elif task.execution_mode == ExecutionMode.BATCH:
                result = await self._execute_batch(handler, params, task.timeout)
            else:
                result = await self._execute_sync(handler, params, task.timeout)
            
            # Update execution
            execution.status = ExecutionStatus.SUCCEEDED
            execution.result = result
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = (
                (execution.completed_at - execution.started_at).total_seconds() * 1000
                if execution.started_at else None
            )
            
            logger.info(f"Task execution succeeded: {execution_id}")
            
        except TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            execution.error_message = "Task execution timed out"
            logger.error(f"Task execution timed out: {execution_id}")
            
        except Exception as e:
            execution.error_message = str(e)
            execution.attempts += 1
            
            # Retry logic
            if execution.attempts < execution.max_attempts:
                execution.status = ExecutionStatus.FAILED
                logger.warning(f"Task execution failed, will retry: {execution_id}")
            else:
                execution.status = ExecutionStatus.FAILED
                logger.error(f"Task execution failed: {execution_id} - {e}")
        
        finally:
            self.running_executions -= 1
        
        return execution
    
    async def _execute_sync(
        self,
        handler: Callable,
        params: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute task synchronously"""
        # In real implementation, use asyncio.wait_for for timeout
        result = await handler(params)
        return result
    
    async def _execute_async(
        self,
        handler: Callable,
        params: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute task asynchronously"""
        # In real implementation, use task queue (Celery, RQ, etc.)
        result = await handler(params)
        return result
    
    async def _execute_batch(
        self,
        handler: Callable,
        params: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute batch task"""
        # In real implementation, process batch items
        result = await handler(params)
        return result
    
    async def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """
        Get execution by ID
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Task execution if found, None otherwise
        """
        return self.executions.get(execution_id)
    
    async def list_executions(
        self,
        task_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None
    ) -> List[TaskExecution]:
        """
        List executions
        
        Args:
            task_id: Task ID filter
            status: Execution status filter
            
        Returns:
            List of task executions
        """
        executions = list(self.executions.values())
        
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        # Sort by started_at desc
        executions.sort(key=lambda e: e.started_at or datetime.utcnow(), reverse=True)
        
        return executions
    
    async def cancel_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """
        Cancel execution
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Updated task execution
        """
        execution = self.executions.get(execution_id)
        if not execution:
            logger.warning(f"Execution not found: {execution_id}")
            return None
        
        if execution.status in [ExecutionStatus.QUEUED, ExecutionStatus.EXECUTING]:
            execution.status = ExecutionStatus.CANCELLED
            logger.info(f"Execution cancelled: {execution_id}")
        
        return execution
    
    async def get_execution_analytics(self) -> Dict[str, Any]:
        """
        Get execution analytics
        
        Returns:
            Execution statistics
        """
        total_executions = len(self.executions)
        
        # By status
        by_status = {}
        for execution in self.executions.values():
            status = execution.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By task
        by_task = {}
        for execution in self.executions.values():
            task_id = execution.task_id
            by_task[task_id] = by_task.get(task_id, 0) + 1
        
        # Success rate
        succeeded = by_status.get("succeeded", 0)
        failed = by_status.get("failed", 0)
        total_finished = succeeded + failed
        success_rate = (succeeded / total_finished * 100) if total_finished > 0 else 0
        
        # Average duration
        durations = [e.duration_ms for e in self.executions.values() if e.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_executions": total_executions,
            "running_executions": self.running_executions,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "by_status": by_status,
            "by_task": by_task
        }