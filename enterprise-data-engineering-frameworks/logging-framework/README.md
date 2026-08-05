# Logging Framework

Structured logging with correlation IDs and JSON output.

```python
from logging_framework.logger import get_logger, set_correlation_id
set_correlation_id('req-123'); log=get_logger('myapp',json_output=True); log.info('Processing',user_id=42)
```
