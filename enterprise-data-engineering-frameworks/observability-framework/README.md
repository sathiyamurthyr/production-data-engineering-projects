# Observability Framework

Observability with metrics, logs, tracing, SLIs, SLOs, and dashboards.

```python
from observability_framework.system import ObservabilitySystem, SLI, SLIType, SLO
o=ObservabilitySystem(); o.record_sli(SLI('avail',SLIType.AVAILABILITY,0.999,0.99))
```
