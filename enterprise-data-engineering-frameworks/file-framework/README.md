# File Framework

File ingestion for CSV, JSON, Parquet, XML, Excel with schema inference.

```python
from file_framework.handler import FileIngestionManager
mgr=FileIngestionManager(); data=mgr.read('data.csv'); mgr.write('out.json', data)
```
