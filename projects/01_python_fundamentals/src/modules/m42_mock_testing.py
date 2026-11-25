"""
================================================================================
MODULE 42: Mock Testing API & Database Calls
================================================================================
1. EXPLANATION:
`unittest.mock` mocks external dependencies (REST APIs, DB connections) during test execution.

2. BUSINESS USE CASE:
Mock external API calls in unit tests to ensure fast, deterministic CI pipeline runs.
"""
from unittest.mock import MagicMock

def fetch_and_process(api_client: MagicMock) -> int:
    """Fetch records using injected API client and return count."""
    data = api_client.get_records()
    return len(data)

if __name__ == "__main__":
    mock_client = MagicMock()
    mock_client.get_records.return_value = [{"id": 1}, {"id": 2}]
    count = fetch_and_process(mock_client)
    print("Mocked Record Count:", count)
