# Platform SDK

Project generator, pipeline generator, config generator, and template engine.

```python
from platform_sdk.generator import ProjectGenerator, ProjectTemplate
g=ProjectGenerator(); g.register_template(ProjectTemplate(name='basic',files={'main.py':'print(1)'}))
g.generate('basic','my_project')
```
