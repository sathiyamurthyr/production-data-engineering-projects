# Batch Framework

Batch processing with Spark, partitioning, and checkpointing.

```python
from batch_framework.processor import BatchProcessor, BatchJob
BatchProcessor('daily').add_job(BatchJob('process', fn, partition_key='date')).run(data)
```
