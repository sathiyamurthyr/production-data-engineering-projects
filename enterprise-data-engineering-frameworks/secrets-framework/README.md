# Secrets Framework

Secrets management with AWS, Azure, Vault, and env providers.

```python
from secrets_framework.provider import SecretsManager, EnvSecretProvider
m=SecretsManager(); m.add_provider(EnvSecretProvider()); m.get_secret('DB_PASSWORD')
```
