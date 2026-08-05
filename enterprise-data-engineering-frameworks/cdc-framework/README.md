# CDC Framework

Change Data Capture with log-based, timestamp-based, checkpointing, and DLQ.

```python
from cdc_framework.capture import TimestampCDC, CDCProcessor
cdc=TimestampCDC('updated_at'); proc=CDCProcessor()
proc.process(cdc.capture(records))
```
