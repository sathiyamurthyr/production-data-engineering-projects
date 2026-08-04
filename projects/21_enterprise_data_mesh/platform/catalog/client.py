"""Data Mesh Catalog Client."""

from typing import Any

import httpx
from loguru import logger

from .models import DataProduct, ProductHealth, ProductSearchResult


class CatalogClient:
    """Client for interacting with the Data Mesh Catalog."""

    def __init__(self, catalog_url: str, api_key: str | None = None):
        self.catalog_url = catalog_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.catalog_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=30.0,
        )

    async def register_product(self, product: DataProduct) -> bool:
        """Register a data product in the catalog."""
        logger.info(f"Registering product: {product.fully_qualified_name}")
        response = await self._client.post(
            "/api/v1/products",
            json=product.model_dump(mode="json"),
        )
        response.raise_for_status()
        return response.json().get("success", False)

    async def get_product(self, domain: str, name: str) -> DataProduct | None:
        """Get a data product by domain and name."""
        response = await self._client.get(f"/api/v1/products/{domain}/{name}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return DataProduct(**response.json())

    async def search_products(
        self,
        domain: str | None = None,
        owner: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductSearchResult:
        """Search for data products with filters."""
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if domain:
            params["domain"] = domain
        if owner:
            params["owner"] = owner
        if tags:
            params["tags"] = ",".join(tags)

        response = await self._client.get("/api/v1/products/search", params=params)
        response.raise_for_status()
        return ProductSearchResult(**response.json())

    async def update_product_status(
        self,
        domain: str,
        name: str,
        status: str,
    ) -> bool:
        """Update product status (certified, deprecated, retired)."""
        logger.info(f"Updating status for {domain}.{name} to {status}")
        response = await self._client.patch(
            f"/api/v1/products/{domain}/{name}/status",
            json={"status": status},
        )
        response.raise_for_status()
        return response.json().get("success", False)

    async def delete_product(self, domain: str, name: str) -> bool:
        """Delete a data product from the catalog."""
        logger.info(f"Deleting product: {domain}.{name}")
        response = await self._client.delete(f"/api/v1/products/{domain}/{name}")
        response.raise_for_status()
        return response.json().get("success", False)

    async def get_product_health(self, domain: str, name: str) -> ProductHealth:
        """Get health metrics for a data product."""
        response = await self._client.get(f"/api/v1/products/{domain}/{name}/health")
        response.raise_for_status()
        return ProductHealth(**response.json())

    async def get_lineage(self, domain: str, name: str) -> list[str]:
        """Get upstream lineage for a data product."""
        response = await self._client.get(f"/api/v1/products/{domain}/{name}/lineage/upstream")
        response.raise_for_status()
        return response.json().get("upstream", [])

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self._client.aclose()

    async def __aenter__(self) -> "CatalogClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()