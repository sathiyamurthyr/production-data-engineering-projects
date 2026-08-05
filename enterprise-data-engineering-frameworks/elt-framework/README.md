# ELT Framework

ELT framework with warehouse-native transforms and dbt-style models.

```python
from elt_framework.pipeline import ELTPipeline, ELTModel
ELTPipeline('analytics').add_model(ELTModel('stg','SELECT * FROM raw')).add_model(ELTModel('mart','SELECT * FROM stg',depends_on=['stg'])).run()
```
