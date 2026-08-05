# Monitoring Framework

Pipeline monitoring with metrics, health checks, and alerting.

```python
from monitoring_framework.monitor import MonitoringEngine, HealthCheck
e=MonitoringEngine(); e.add_health_check(HealthCheck('db',check_fn)); e.run_health_checks()
```
