# Streaming Framework

Streaming with Kafka, checkpointing, DLQ, watermarks, and state management.

```python
from streaming_framework.pipeline import StreamingPipeline, ListSource, ListSink
StreamingPipeline('job').source(ListSource(data,100)).transform(filter_fn).sink(ListSink()).run()
```
