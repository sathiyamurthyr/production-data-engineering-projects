# ETL Framework

ETL framework with CSV, JSON, Parquet, REST, Kafka connectors, SCD Type 2, and incremental loads.

```python
from etl_framework.pipeline import ETLPipeline, CSVExtractor, JSONLoader, drop_nulls
ETLPipeline('sales').extract(CSVExtractor('sales.csv')).transform(drop_nulls('amt')).load(JSONLoader('out.json')).run()
```
