"""Data Mesh Catalog Service."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .models import (
    DataProduct,
    DataSchema,
    LineageInfo,
    ProductHealth,
    ProductMetadata,
    QualityCriteria,
    SlaDefinition,
    SlaStatus,
)


class CatalogService:
    """Local catalog service for managing data products."""

    def __init__(self, storage_path: str = "catalog_data.json"):
        self.storage_path = Path(storage_path)
        self._products: dict[str, DataProduct] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load catalog from storage."""
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                data = json.loads(f.read())
                for product_data in data.get("products", []):
                    self._products[product_data["name"]] = DataProduct(**product_data)
        logger.info(f"Loaded {len(self._products)} products from catalog")

    def _save_catalog(self) -> None:
        """Save catalog to storage."""
        data = {
            "products": [p.model_dump(mode="json") for p in self._products.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved catalog to storage")

    def register_product(self, product: DataProduct) -> bool:
        """Register a data product in the catalog."""
        key = f"{product.domain}.{product.name}"
        self._products[key] = product
        self._save_catalog()
        logger.info(f"Registered product: {key}")
        return True

    def get_product(self, domain: str, name: str) -> DataProduct | None:
        """Get a data product by domain and name."""
        key = f"{domain}.{name}"
        return self._products.get(key)

    def search_products(
        self,
        domain: str | None = None,
        owner: str | None = None,
        tags: list[str] | None = None,
    ) -> list[DataProduct]:
        """Search for data products."""
        results = list(self._products.values())

        if domain:
            results = [p for p in results if p.domain == domain]
        if owner:
            results = [p for p in results if p.owner == owner]
        if tags:
            results = [p for p in results if any(t in p.metadata.tags for t in tags)]

        return results

    def update_status(self, domain: str, name: str, status: str) -> bool:
        """Update product status."""
        product = self.get_product(domain, name)
        if not product:
            return False

        product.status = status
        self._save_catalog()
        logger.info(f"Updated {domain}.{name} status to {status}")
        return True

    def get_health(self, domain: str, name: str) -> ProductHealth:
        """Get health metrics for a product."""
        product = self.get_product(domain, name)
        if not product:
            raise ValueError(f"Product {domain}.{name} not found")

        # Calculate freshness status based on SLA
        freshness_status = SlaStatus.HEALTHY
        quality_score = 95.0  # Placeholder - would integrate with monitoring service
        availability = 99.9  # Placeholder - would integrate with monitoring service

        return ProductHealth(
            freshness_status=freshness_status,
            quality_score=quality_score,
            availability=availability,
            last_updated=datetime.now(),
            next_update=None,
        )

    def get_lineage(self, domain: str, name: str) -> LineageInfo:
        """Get lineage information for a product."""
        product = self.get_product(domain, name)
        if not product:
            raise ValueError(f"Product {domain}.{name} not found")

        # Return lineage info (would integrate with actual lineage service)
        return LineageInfo(
            upstream=[],
            downstream=[],
            transformation_steps=["bronze_ingestion", "silver_cleaning", "gold_curation"],
            last_lineage_update=datetime.now(),
        )


def create_sample_product() -> DataProduct:
    """Create a sample data product for testing."""
    return DataProduct(
        name="customer_profile",
        domain="customer",
        version="1.0.0",
        owner="customer-team@example.com",
        description="Master customer profile data",
        schema=DataSchema(
            fields=[
                {"name": "customer_id", "type": "string", "required": True},
                {"name": "email", "type": "string", "required": True},
                {"name": "created_at", "type": "timestamp", "required": True},
            ],
            format="delta",
            partition_by=["created_date"],
        ),
        sla=SlaDefinition(
            freshness="24h",
            availability=99.9,
            support_level="24x7",
        ),
        quality=QualityCriteria(
            completeness=0.99,
            uniqueness=1.0,
            validity=0.99,
            freshness_hours=24,
        ),
        metadata=ProductMetadata(
            domain="customer",
            owner="customer-team@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description="Master customer profile data",
            classification="internal",
            tags=["customer", "profile", "master"],
        ),
    )