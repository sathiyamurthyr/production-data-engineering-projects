"""
Automation Scheduler for Cross-Cloud Platform

This module provides scheduling capabilities for automation tasks.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
from croniter import croniter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScheduleStatus(str, Enum):
    """Schedule status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleType(str, Enum):
    """Schedule types"""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"


class Schedule(BaseModel):
    """Schedule definition"""
    schedule_id: str
    name: str
    description: str
    schedule_type: ScheduleType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    max_runs: Optional[int] = None
    run_count: int = 0
    status: ScheduleStatus
    cloud: str
    task_action: str
    task_parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AutomationScheduler:
    """
    Cross-cloud automation scheduler
    
    This service provides:
    - Task scheduling
    - Cron-based execution
    - Interval-based execution
    - Schedule management
    """
    
    def __init__(self, config: Dict):
        """
        Initialize automation scheduler
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.schedules: Dict[str, Schedule] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("Automation Scheduler initialized")
    
    async def create_schedule(
        self,
        schedule_id: str,
        name: str,
        description: str,
        schedule_type: ScheduleType,
        task_action: str,
        task_parameters: Dict[str, Any],
        cloud: str,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schedule:
        """
        Create schedule
        
        Args:
            schedule_id: Schedule ID
            name: Schedule name
            description: Schedule description
            schedule_type: Schedule type
            task_action: Task action to execute
            task_parameters: Task parameters
            cloud: Cloud provider
            cron_expression: Cron expression (for cron schedules)
            interval_seconds: Interval in seconds (for interval schedules)
            start_time: Start time
            end_time: End time (optional)
            max_runs: Maximum runs (optional)
            metadata: Additional metadata
            
        Returns:
            Schedule
        """
        logger.info(f"Creating schedule: {schedule_id}")
        
        if schedule_id in self.schedules:
            raise ValueError(f"Schedule already exists: {schedule_id}")
        
        if start_time is None:
            start_time = datetime.utcnow()
        
        schedule = Schedule(
            schedule_id=schedule_id,
            name=name,
            description=description,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            start_time=start_time,
            end_time=end_time,
            max_runs=max_runs,
            status=ScheduleStatus.ACTIVE,
            cloud=cloud,
            task_action=task_action,
            task_parameters=task_parameters,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.schedules[schedule_id] = schedule
        
        logger.info(f"Schedule created: {schedule_id}")
        return schedule
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get schedule by ID
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Schedule if found, None otherwise
        """
        return self.schedules.get(schedule_id)
    
    async def evaluate_schedules(self, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Evaluate schedules and trigger executions
        
        Args:
            current_time: Current time (defaults to now)
            
        Returns:
            List of triggered executions
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        triggered = []
        
        for schedule in self.schedules.values():
            if schedule.status != ScheduleStatus.ACTIVE:
                continue
            
            # Check if schedule should run
            should_run = await self._should_run(schedule, current_time)
            
            if should_run:
                # Create execution
                execution = await self._create_execution(schedule, current_time)
                triggered.append(execution)
        
        return triggered
    
    async def _should_run(self, schedule: Schedule, current_time: datetime) -> bool:
        """
        Check if schedule should run
        
        Args:
            schedule: Schedule
            current_time: Current time
            
        Returns:
            True if should run, False otherwise
        """
        # Check start time
        if current_time < schedule.start_time:
            return False
        
        # Check end time
        if schedule.end_time and current_time > schedule.end_time:
            schedule.status = ScheduleStatus.COMPLETED
            return False
        
        # Check max runs
        if schedule.max_runs and schedule.run_count >= schedule.max_runs:
            schedule.status = ScheduleStatus.COMPLETED
            return False
        
        # Check schedule type
        if schedule.schedule_type == ScheduleType.CRON:
            return self._check_cron(schedule, current_time)
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            return self._check_interval(schedule, current_time)
        elif schedule.schedule_type == ScheduleType.ONE_TIME:
            return self._check_one_time(schedule, current_time)
        
        return False
    
    def _check_cron(self, schedule: Schedule, current_time: datetime) -> bool:
        """Check cron schedule"""
        if not schedule.cron_expression:
            return False
        
        # Get last execution time
        last_execution = None
        if self.execution_history:
            last_execution = self.execution_history[-1].get("executed_at")
        
        # Check if current time matches cron
        cron = croniter(schedule.cron_expression, current_time)
        next_run = cron.get_next(datetime)
        
        # If next run is very close to current time, trigger
        time_diff = abs((next_run - current_time).total_seconds())
        return time_diff < 60  # Within 1 minute
    
    def _check_interval(self, schedule: Schedule, current_time: datetime) -> bool:
        """Check interval schedule"""
        if not schedule.interval_seconds:
            return False
        
        # Get last execution time
        last_execution = None
        for history in reversed(self.execution_history):
            if history.get("schedule_id") == schedule.schedule_id:
                last_execution = history.get("executed_at")
                break
        
        if not last_execution:
            return True
        
        # Check if interval has passed
        time_since_last = (current_time - last_execution).total_seconds()
        return time_since_last >= schedule.interval_seconds
    
    def _check_one_time(self, schedule: Schedule, current_time: datetime) -> bool:
        """Check one-time schedule"""
        # Run if current time is at or after start time and hasn't run yet
        return schedule.run_count == 0 and current_time >= schedule.start_time
    
    async def _create_execution(self, schedule: Schedule, executed_at: datetime) -> Dict[str, Any]:
        """
        Create execution record
        
        Args:
            schedule: Schedule
            executed_at: Execution time
            
        Returns:
            Execution record
        """
        execution = {
            "schedule_id": schedule.schedule_id,
            "task_action": schedule.task_action,
            "task_parameters": schedule.task_parameters,
            "cloud": schedule.cloud,
            "executed_at": executed_at,
            "run_count": schedule.run_count + 1
        }
        
        self.execution_history.append(execution)
        
        # Update schedule
        schedule.run_count += 1
        schedule.updated_at = executed_at
        
        logger.info(f"Schedule triggered: {schedule.schedule_id}")
        return execution
    
    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Pause schedule
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Updated schedule
        """
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            logger.warning(f"Schedule not found: {schedule_id}")
            return None
        
        schedule.status = ScheduleStatus.PAUSED
        schedule.updated_at = datetime.utcnow()
        
        logger.info(f"Schedule paused: {schedule_id}")
        return schedule
    
    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Resume schedule
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Updated schedule
        """
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            logger.warning(f"Schedule not found: {schedule_id}")
            return None
        
        schedule.status = ScheduleStatus.ACTIVE
        schedule.updated_at = datetime.utcnow()
        
        logger.info(f"Schedule resumed: {schedule_id}")
        return schedule
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete schedule
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            True if deleted, False otherwise
        """
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            logger.info(f"Schedule deleted: {schedule_id}")
            return True
        
        logger.warning(f"Schedule not found: {schedule_id}")
        return False
    
    async def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
        cloud: Optional[str] = None
    ) -> List[Schedule]:
        """
        List schedules
        
        Args:
            status: Schedule status filter
            cloud: Cloud provider filter
            
        Returns:
            List of schedules
        """
        schedules = list(self.schedules.values())
        
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        if cloud:
            schedules = [s for s in schedules if s.cloud == cloud]
        
        # Sort by created_at desc
        schedules.sort(key=lambda s: s.created_at, reverse=True)
        
        return schedules
    
    async def get_execution_history(
        self,
        schedule_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution history
        
        Args:
            schedule_id: Schedule ID filter (optional)
            limit: Maximum results
            
        Returns:
            List of execution records
        """
        history = self.execution_history
        
        if schedule_id:
            history = [h for h in history if h.get("schedule_id") == schedule_id]
        
        # Sort by executed_at desc
        history.sort(key=lambda h: h.get("executed_at", datetime.utcnow()), reverse=True)
        
        return history[:limit]
    
    async def get_scheduler_analytics(self) -> Dict[str, Any]:
        """
        Get scheduler analytics
        
        Returns:
            Scheduler statistics
        """
        total_schedules = len(self.schedules)
        
        # By status
        by_status = {}
        for schedule in self.schedules.values():
            status = schedule.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By type
        by_type = {}
        for schedule in self.schedules.values():
            schedule_type = schedule.schedule_type.value
            by_type[schedule_type] = by_type.get(schedule_type, 0) + 1
        
        # By cloud
        by_cloud = {}
        for schedule in self.schedules.values():
            cloud = schedule.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # Total executions
        total_executions = len(self.execution_history)
        
        return {
            "total_schedules": total_schedules,
            "total_executions": total_executions,
            "by_status": by_status,
            "by_type": by_type,
            "by_cloud": by_cloud
        }