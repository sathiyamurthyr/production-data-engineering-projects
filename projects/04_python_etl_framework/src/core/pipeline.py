"""
Pipeline Orchestration Module

Core pipeline engine for executing ETL workflows.
"""

import uuid
from typing import Protocol, Any, Optional
from datetime import datetime, timezone
import time

from etl_framework.core.context import ExecutionContext, PipelineStatus


class Extractor(Protocol):
    """Protocol for data extraction."""
    
    def extract(self) -> list[dict[str, Any]]:
        """Extract data from source."""
        ...


class Transformer(Protocol):
    """Protocol for data transformation."""
    
    def transform(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform extracted data."""
        ...


class Loader(Protocol):
    """Protocol for data loading."""
    
    def load(self, records: list[dict[str, Any]]) -> int:
        """Load transformed data to target. Returns count of records loaded."""
        ...


class RetryHandler:
    """Handles retry logic with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute_with_retry(self, func: callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
        
        raise last_exception


class Pipeline:
    """
    Enterprise ETL Pipeline orchestrator.
    
    Implements clean architecture with configurable components
    for extraction, transformation, and loading.
    """
    
    def __init__(
        self,
        name: str,
        extractor: Extractor,
        loader: Loader,
        transformer: Optional[Transformer] = None,
        max_retries: int = 3,
        batch_size: int = 1000,
    ):
        self.name = name
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.retry_handler = RetryHandler(max_retries=max_retries)
    
    def run(self) -> ExecutionContext:
        """Execute the full pipeline."""
        run_id = str(uuid.uuid4())
        context = ExecutionContext(
            pipeline_name=self.name,
            run_id=run_id,
            start_time=datetime.now(timezone.utc),
        )
        
        try:
            context.status = PipelineStatus.RUNNING
            context.metrics["steps_completed"] = 0
            
            # Extract phase
            records = self.retry_handler.execute_with_retry(self.extractor.extract)
            context.records_processed = len(records)
            context.metrics["steps_completed"] = 1
            
            # Transform phase
            if self.transformer:
                records = self.retry_handler.execute_with_retry(
                    self.transformer.transform, records
                )
                context.metrics["steps_completed"] = 2
            
            # Load phase (batch processing)
            total_loaded = 0
            for i in range(0, len(records), self.batch_size):
                batch = records[i:i + self.batch_size]
                loaded = self.retry_handler.execute_with_retry(
                    self.loader.load, batch
                )
                total_loaded += loaded
            
            context.metrics["records_loaded"] = total_loaded
            context.metrics["steps_completed"] = 3
            context.status = PipelineStatus.SUCCESS
            
        except Exception as e:
            context.status = PipelineStatus.FAILED
            context.error_count = 1
            context.metrics["error_message"] = str(e)
            raise
        
        return context