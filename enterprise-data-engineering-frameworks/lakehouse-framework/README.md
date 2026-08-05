# Lakehouse Framework

Lakehouse management with Delta Lake, ACID, time travel, and optimization.

```python
from lakehouse_framework.manager import LakehouseManager
m=LakehouseManager(); t=m.create_table('orders'); t.write([{'id':1,'amt':100}]); t.read()
```
