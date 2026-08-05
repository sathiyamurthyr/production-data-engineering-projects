# Lineage Framework

Lineage with column-level tracking, impact analysis, and visual graph.

```python
from lineage_framework.tracker import LineageNode, LineageEdge, LineageTracker
t=LineageTracker(); s=t.add_node(LineageNode(name='raw.orders')); d=t.add_node(LineageNode(name='mart.sales'))
t.add_edge(LineageEdge(s,d)); t.impact_analysis(s)
```
