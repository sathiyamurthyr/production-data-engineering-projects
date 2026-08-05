# API Framework

REST/GraphQL ingestion with pagination, auth, rate limiting, and retry.

```python
from api_framework.client import APIConfig, APIClient
client=APIClient(APIConfig(base_url='https://api.example.com', auth_token='token'))
data=client.fetch_all('users', data_path='results')
```
