"""
Log Aggregator for Cross-Cloud Observability

This module provides unified log management across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    """Log entry"""
    log_id: str
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
    resource_id: str
    resource_type: str
    cloud: str
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LogAggregator:
    """
    Cross-cloud log aggregator
    
    This service provides:
    - Log collection and aggregation
    - Cross-cloud log normalization
    - Log querying and filtering
    - Log analytics
    """
    
    def __init__(self, config: Dict):
        """
        Initialize log aggregator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logs: List[LogEntry] = []
        self.retention_days = config.get("retention_days", 90)
        
        logger.info("Log Aggregator initialized")
    
    async def ingest_log(
        self,
        level: LogLevel,
        message: str,
        source: str,
        resource_id: str,
        resource_type: str,
        cloud: str,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> LogEntry:
        """
        Ingest log entry
        
        Args:
            level: Log level
            message: Log message
            source: Log source
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            labels: Log labels
            metadata: Additional metadata
            timestamp: Timestamp (defaults to now)
            
        Returns:
            Log entry
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Generate log ID
        log_id = f"log-{timestamp.strftime('%Y%m%d%H%M%S')}-{source[:8]}"
        
        log_entry = LogEntry(
            log_id=log_id,
            timestamp=timestamp,
            level=level,
            message=message,
            source=source,
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.logs.append(log_entry)
        
        # Cleanup old logs
        await self._cleanup_old_logs()
        
        logger.info(f"Log ingested: {log_id}")
        return log_entry
    
    async def _cleanup_old_logs(self) -> None:
        """Cleanup old logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        self.logs = [
            log for log in self.logs
            if log.timestamp >= cutoff_date
        ]
    
    async def query_logs(
        self,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        cloud: Optional[str] = None,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[LogEntry]:
        """
        Query logs
        
        Args:
            resource_id: Resource ID filter
            resource_type: Resource type filter
            cloud: Cloud provider filter
            level: Log level filter
            source: Source filter
            start_time: Start time filter
            end_time: End time filter
            search: Search query
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of log entries
        """
        results = self.logs
        
        # Apply filters
        if resource_id:
            results = [log for log in results if log.resource_id == resource_id]
        
        if resource_type:
            results = [log for log in results if log.resource_type == resource_type]
        
        if cloud:
            results = [log for log in results if log.cloud == cloud]
        
        if level:
            results = [log for log in results if log.level == level]
        
        if source:
            results = [log for log in results if log.source == source]
        
        if start_time:
            results = [log for log in results if log.timestamp >= start_time]
        
        if end_time:
            results = [log for log in results if log.timestamp <= end_time]
        
        if search:
            search_lower = search.lower()
            results = [
                log for log in results
                if search_lower in log.message.lower()
            ]
        
        # Sort by timestamp desc
        results.sort(key=lambda log: log.timestamp, reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]
    
    async def get_log(self, log_id: str) -> Optional[LogEntry]:
        """
        Get log by ID
        
        Args:
            log_id: Log ID
            
        Returns:
            Log entry if found, None otherwise
        """
        for log in self.logs:
            if log.log_id == log_id:
                return log
        return None
    
    async def get_resource_logs(
        self,
        resource_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None
    ) -> List[LogEntry]:
        """
        Get logs for resource
        
        Args:
            resource_id: Resource ID
            start_time: Start time (optional)
            end_time: End time (optional)
            level: Log level filter (optional)
            
        Returns:
            List of log entries
        """
        return await self.query_logs(
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            level=level
        )
    
    async def get_error_logs(
        self,
        cloud: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[LogEntry]:
        """
        Get error logs
        
        Args:
            cloud: Cloud provider filter
            resource_type: Resource type filter
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            List of error log entries
        """
        return await self.query_logs(
            cloud=cloud,
            resource_type=resource_type,
            level=LogLevel.ERROR,
            start_time=start_time,
            end_time=end_time
        )
    
    async def get_log_analytics(self) -> Dict[str, Any]:
        """
        Get log analytics
        
        Returns:
            Log statistics
        """
        total_logs = len(self.logs)
        
        # By level
        by_level = {}
        for log in self.logs:
            level = log.level.value
            by_level[level] = by_level.get(level, 0) + 1
        
        # By cloud
        by_cloud = {}
        for log in self.logs:
            cloud = log.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By source
        by_source = {}
        for log in self.logs:
            source = log.source
            by_source[source] = by_source.get(source, 0) + 1
        
        # Error count
        error_count = len([log for log in self.logs if log.level == LogLevel.ERROR])
        
        # Recent logs (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_logs = len([log for log in self.logs if log.timestamp >= cutoff])
        
        return {
            "total_logs": total_logs,
            "recent_logs_1h": recent_logs,
            "error_count": error_count,
            "by_level": by_level,
            "by_cloud": by_cloud,
            "by_source": by_source
        }