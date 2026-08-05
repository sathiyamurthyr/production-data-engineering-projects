# Config Framework

Hierarchical configuration: env, file, vault, CLI, dynamic config.

```python
from config_framework.manager import ConfigManager
m=ConfigManager(); m.add_file('config.yaml'); m.add_env(); m.get('database.host')
```
