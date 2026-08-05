# Ingestion Framework

Unified ingestion across APIs, files, databases, and streams.

```python
from ingestion_framework.manager import IngestionManager, IngestionSource
mgr=IngestionManager(); mgr.register(MySource()); mgr.ingest('my_source')
```
