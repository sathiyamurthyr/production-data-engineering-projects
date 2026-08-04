"""
Automation Engine for Cross-Cloud Platform

This module provides automation orchestration across Azure and AWS.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Task(BaseModel):
    """Automation task"""
    task_id: str
    name: str
    description: str
    action: str
    parameters: Dict[str, Any]
    status: TaskStatus
    cloud: str
    resource_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AutomationEngine:
    """
    Cross-cloud automation engine
    
    This service provides:
    - Task orchestration
    - Cross-cloud automation
    - Retry and error handling
    - Task scheduling
    """
    
    def __init__(self, config: Dict):
        """
        Initialize automation engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.max_concurrent_tasks = config.get("max_concurrent_tasks", 10)
        self.running_tasks = 0
        
        logger.info("Automation Engine initialized")
    
    def register_handler(self, action: str, handler: Callable) -> None:
        """
        Register task handler
        
        Args:
            action: Action name
            handler: Handler function
        """
        self.task_handlers[action] = handler
        logger.info(f"Handler registered for action: {action}")
    
    async def create_task(
        self,
        task_id: str,
        name: str,
        description: str,
        action: str,
        parameters: Dict[str, Any],
        cloud: str,
        resource_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Task:
        """
        Create automation task
        
        Args:
            task_id: Task ID
            name: Task name
            description: Task description
            action: Action to perform
            parameters: Action parameters
            cloud: Cloud provider
            resource_id: Resource ID (optional)
            max_retries: Maximum retry attempts
            
        Returns:
            Task
        """
        logger.info(f"Creating automation task: {task_id}")
        
        if task_id in self.tasks:
            raise ValueError(f"Task already exists: {task_id}")
        
        task = Task(
            task_id=task_id,
            name=name,
            description=description,
            action=action,
            parameters=parameters,
            status=TaskStatus.PENDING,
            cloud=cloud,
            resource_id=resource_id,
            max_retries=max_retries,
            created_at=datetime.utcnow()
        )
        
        self.tasks[task_id] = task
        
        logger.info(f"Automation task created: {task_id}")
        return task
    
    async def execute_task(self, task_id: str) -> Optional[Task]:
        """
        Execute automation task
        
        Args:
            task_id: Task ID
            
        Returns:
            Updated task
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return None
        
        logger.info(f"Executing task: {task_id}")
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.running_tasks += 1
        
        try:
            # Get handler for action
            handler = self.task_handlers.get(task.action)
            if not handler:
                raise ValueError(f"No handler registered for action: {task.action}")
            
            # Execute handler
            result = await handler(task.parameters)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"Task failed: {task_id} - {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.error_message = str(e)
                logger.info(f"Retrying task: {task_id} (attempt {task.retry_count}/{task.max_retries})")
            else:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        
        finally:
            self.running_tasks -= 1
        
        return task
    
    async def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        Cancel automation task
        
        Args:
            task_id: Task ID
            
        Returns:
            Updated task
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return None
        
        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            logger.info(f"Task cancelled: {task_id}")
        
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        cloud: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Task]:
        """
        List tasks
        
        Args:
            status: Task status filter
            cloud: Cloud provider filter
            action: Action filter
            
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if cloud:
            tasks = [t for t in tasks if t.cloud == cloud]
        
        if action:
            tasks = [t for t in tasks if t.action == action]
        
        # Sort by created_at desc
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks
    
    async def retry_failed_task(self, task_id: str) -> Optional[Task]:
        """
        Retry failed task
        
        Args:
            task_id: Task ID
            
        Returns:
            Updated task
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return None
        
        if task.status == TaskStatus.FAILED:
            task.status = TaskStatus.PENDING
            task.retry_count = 0
            task.error_message = None
            task.result = None
            
            logger.info(f"Task reset for retry: {task_id}")
        
        return task
    
    async def get_automation_analytics(self) -> Dict[str, Any]:
        """
        Get automation analytics
        
        Returns:
            Automation statistics
        """
        total_tasks = len(self.tasks)
        
        # By status
        by_status = {}
        for task in self.tasks.values():
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By action
        by_action = {}
        for task in self.tasks.values():
            action = task.action
            by_action[action] = by_action.get(action, 0) + 1
        
        # By cloud
        by_cloud = {}
        for task in self.tasks.values():
            cloud = task.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # Success rate
        completed = by_status.get("completed", 0)
        failed = by_status.get("failed", 0)
        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "running_tasks": self.running_tasks,
            "success_rate": success_rate,
            "by_status": by_status,
            "by_action": by_action,
            "by_cloud": by_cloud
        }