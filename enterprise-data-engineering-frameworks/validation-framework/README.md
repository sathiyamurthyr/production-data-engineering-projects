# Validation Framework

Data validation with contracts, custom validators, and quality reports.

```python
from validation_framework.engine import DataContract, ValidationRule, ValidationEngine
c=DataContract('users').add_rule(ValidationRule('name_req','name','required'))
e=ValidationEngine(); e.register_contract(c); e.validate('users', {'name':'Alice'})
```
