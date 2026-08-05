# Governance Framework

Data governance with policies, access control, compliance, audit, and retention.

```python
from governance_framework.governance import GovernanceEngine, AccessPolicy, AccessLevel
e=GovernanceEngine(); e.add_access_policy(AccessPolicy('p','table1','user1',AccessLevel.READ))
```
