# Quality Framework

Data quality with schema validation, business rules, duplicates, freshness, completeness.

```python
from quality_framework.checks import SchemaCheck, DuplicateCheck, QualityReporter
r=QualityReporter(); r.run_checks(data, [SchemaCheck({'id':int}), DuplicateCheck(['id'])])
print(r.overall_score(), r.all_passed())
```
