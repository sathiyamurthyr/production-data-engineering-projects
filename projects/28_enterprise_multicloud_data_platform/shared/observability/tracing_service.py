"""
Tracing Service for Cross-Cloud Observability

This module provides distributed tracing across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpanType(str, Enum):
    """Span types"""
    HTTP = "http"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    FUNCTION = "function"
    CACHE = "cache"
    EXTERNAL = "external"


class SpanStatus(str, Enum):
    """Span status"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Span(BaseModel):
    """Trace span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    name: str
    span_type: SpanType
    status: SpanStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    resource_id: str
    resource_type: str
    cloud: str
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class Trace(BaseModel):
    """Distributed trace"""
    trace_id: str
    spans: List[Span]
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus
    resource_id: str
    resource_type: str
    cloud: str


class TracingService:
    """
    Cross-cloud distributed tracing service
    
    This service provides:
    - Distributed trace collection
    - Cross-cloud trace correlation
    - Performance analysis
    - Error tracking
    """
    
    def __init__(self, config: Dict):
        """
        Initialize tracing service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, Span] = {}
        
        logger.info("Tracing Service initialized")
    
    async def start_trace(
        self,
        trace_id: str,
        resource_id: str,
        resource_type: str,
        cloud: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Trace:
        """
        Start new trace
        
        Args:
            trace_id: Trace ID
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            labels: Trace labels
            
        Returns:
            Trace
        """
        logger.info(f"Starting trace: {trace_id}")
        
        trace = Trace(
            trace_id=trace_id,
            spans=[],
            start_time=datetime.utcnow(),
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud
        )
        
        self.traces[trace_id] = trace
        
        logger.info(f"Trace started: {trace_id}")
        return trace
    
    async def start_span(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        span_type: SpanType,
        resource_id: str,
        resource_type: str,
        cloud: str,
        parent_span_id: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Span:
        """
        Start new span
        
        Args:
            trace_id: Trace ID
            span_id: Span ID
            name: Span name
            span_type: Span type
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            parent_span_id: Parent span ID
            labels: Span labels
            
        Returns:
            Span
        """
        logger.info(f"Starting span: {span_id}")
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            status=SpanStatus.OK,
            start_time=datetime.utcnow(),
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud,
            labels=labels or {}
        )
        
        self.spans[span_id] = span
        
        # Add to trace
        trace = self.traces.get(trace_id)
        if trace:
            trace.spans.append(span)
        
        logger.info(f"Span started: {span_id}")
        return span
    
    async def end_span(
        self,
        span_id: str,
        status: SpanStatus,
        error_message: Optional[str] = None
    ) -> Optional[Span]:
        """
        End span
        
        Args:
            span_id: Span ID
            status: Span status
            error_message: Error message if failed
            
        Returns:
            Updated span
        """
        span = self.spans.get(span_id)
        if not span:
            logger.warning(f"Span not found: {span_id}")
            return None
        
        span.end_time = datetime.utcnow()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status
        span.error_message = error_message
        
        logger.info(f"Span ended: {span_id} ({span.duration_ms:.2f}ms)")
        return span
    
    async def end_trace(self, trace_id: str) -> Optional[Trace]:
        """
        End trace
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Updated trace
        """
        trace = self.traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace not found: {trace_id}")
            return None
        
        trace.end_time = datetime.utcnow()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        
        # Determine trace status
        has_error = any(span.status == SpanStatus.ERROR for span in trace.spans)
        trace.status = SpanStatus.ERROR if has_error else SpanStatus.OK
        
        logger.info(f"Trace ended: {trace_id} ({trace.duration_ms:.2f}ms)")
        return trace
    
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """
        Get trace by ID
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace if found, None otherwise
        """
        return self.traces.get(trace_id)
    
    async def get_span(self, span_id: str) -> Optional[Span]:
        """
        Get span by ID
        
        Args:
            span_id: Span ID
            
        Returns:
            Span if found, None otherwise
        """
        return self.spans.get(span_id)
    
    async def get_resource_traces(
        self,
        resource_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Trace]:
        """
        Get traces for resource
        
        Args:
            resource_id: Resource ID
            start_time: Start time (optional)
            end_time: End time (optional)
            
        Returns:
            List of traces
        """
        traces = list(self.traces.values())
        
        # Filter by resource
        traces = [t for t in traces if t.resource_id == resource_id]
        
        if start_time:
            traces = [t for t in traces if t.start_time >= start_time]
        
        if end_time:
            traces = [t for t in traces if t.end_time and t.end_time <= end_time]
        
        # Sort by start_time desc
        traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return traces
    
    async def get_error_traces(
        self,
        cloud: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> List[Trace]:
        """
        Get error traces
        
        Args:
            cloud: Cloud provider filter
            resource_type: Resource type filter
            
        Returns:
            List of error traces
        """
        traces = list(self.traces.values())
        
        # Filter by error status
        traces = [t for t in traces if t.status == SpanStatus.ERROR]
        
        if cloud:
            traces = [t for t in traces if t.cloud == cloud]
        
        if resource_type:
            traces = [t for t in traces if t.resource_type == resource_type]
        
        return traces
    
    async def get_tracing_analytics(self) -> Dict[str, Any]:
        """
        Get tracing analytics
        
        Returns:
            Tracing statistics
        """
        total_traces = len(self.traces)
        total_spans = len(self.spans)
        
        # By status
        by_status = {}
        for trace in self.traces.values():
            status = trace.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # By cloud
        by_cloud = {}
        for trace in self.traces.values():
            cloud = trace.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By span type
        by_span_type = {}
        for span in self.spans.values():
            span_type = span.span_type.value
            by_span_type[span_type] = by_span_type.get(span_type, 0) + 1
        
        # Average duration
        durations = [t.duration_ms for t in self.traces.values() if t.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_traces": total_traces,
            "total_spans": total_spans,
            "error_traces": by_status.get("error", 0),
            "by_cloud": by_cloud,
            "by_span_type": by_span_type,
            "avg_trace_duration_ms": avg_duration
        }