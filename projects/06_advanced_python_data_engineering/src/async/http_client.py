"""
Async HTTP Client for Data Engineering

Production patterns for concurrent API data ingestion.
"""

import asyncio
from typing import Any
import aiohttp
import pandas as pd


class AsyncHTTPClient:
    """
    Async HTTP client for concurrent API calls.
    
    Business Use Case: Parallel API ingestion for data pipelines.
    """

    def __init__(
        self,
        base_url: str,
        max_concurrent: int = 10,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        if self._session:
            await self._session.close()

    async def fetch_one(self, endpoint: str) -> dict[str, Any]:
        """Fetch single endpoint."""
        if not self._session:
            raise RuntimeError("Client not initialized")

        url = f"{self.base_url}/{endpoint}"
        async with self._session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def fetch_all(
        self,
        endpoints: list[str],
    ) -> list[dict[str, Any]]:
        """Fetch multiple endpoints concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def fetch_with_semaphore(endpoint: str) -> dict[str, Any]:
            async with semaphore:
                return await self.fetch_one(endpoint)

        tasks = [fetch_with_semaphore(ep) for ep in endpoints]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def fetch_to_dataframe(
        self,
        endpoints: list[str],
    ) -> pd.DataFrame:
        """Fetch multiple endpoints and combine into DataFrame."""
        results = await self.fetch_all(endpoints)
        valid_results = [
            r for r in results if not isinstance(r, Exception)
        ]
        return pd.DataFrame(valid_results)


async def parallel_api_ingestion(
    base_url: str,
    endpoints: list[str],
    max_concurrent: int = 10,
) -> pd.DataFrame:
    """
    Convenience function for parallel API ingestion.
    
    Business Use Case: Customer data from multiple microservices.
    """
    async with AsyncHTTPClient(base_url, max_concurrent) as client:
        return await client.fetch_to_dataframe(endpoints)