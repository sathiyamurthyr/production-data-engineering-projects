# Metadata Framework

Metadata with business, technical, operational metadata, catalog, and data contracts.

```python
from metadata_framework.catalog import MetadataCatalog, TableMetadata
catalog=MetadataCatalog(); catalog.register_table(TableMetadata(name='users',owner='team1',tags=['pii']))
```
