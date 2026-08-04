"""Data Discovery - Automated data discovery and classification."""

import re
from typing import Any

from ..metadata.models import Asset, AssetType, SensitivityLevel
from ..catalog.catalog import CatalogService
from ..search.search import SearchService


class DataDiscoveryService:
    """Automated data discovery and classification."""

    def __init__(self, catalog: CatalogService, search: SearchService) -> None:
        """Initialize discovery service."""
        self.catalog = catalog
        self.search = search
        self.pii_patterns = self._load_pii_patterns()
        self.sensitive_keywords = self._load_sensitive_keywords()

    def _load_pii_patterns(self) -> dict[str, str]:
        """Load PII detection patterns."""
        return {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "phone": r'\b\+?1?[-.]?(\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4})\b',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }

    def _load_sensitive_keywords(self) -> dict[str, list[str]]:
        """Load sensitive keywords for classification."""
        return {
            "pii": ["email", "ssn", "phone", "address", "name", "birth", "gender", "password"],
            "phi": ["medical", "health", "diagnosis", "patient", "treatment", "prescription", "doctor"],
            "financial": ["account", "balance", "transaction", "payment", "credit", "salary", "income"],
            "confidential": ["secret", "confidential", "internal", "proprietary", "trade"],
        }

    def discover_sensitive_data(self, asset: Asset) -> dict[str, Any]:
        """Discover sensitive data in an asset."""
        findings = {
            "pii": [],
            "phi": [],
            "financial": [],
            "confidence_score": 0.0,
        }
        
        # Check column names
        for column in asset.columns:
            column_name_lower = column.name.lower()
            
            # PII detection
            for keyword in self.sensitive_keywords["pii"]:
                if keyword in column_name_lower:
                    findings["pii"].append({
                        "column": column.name,
                        "type": "pii",
                        "keyword_matched": keyword,
                    })
            
            # PHI detection
            for keyword in self.sensitive_keywords["phi"]:
                if keyword in column_name_lower:
                    findings["phi"].append({
                        "column": column.name,
                        "type": "phi",
                        "keyword_matched": keyword,
                    })
            
            # Financial detection
            for keyword in self.sensitive_keywords["financial"]:
                if keyword in column_name_lower:
                    findings["financial"].append({
                        "column": column.name,
                        "type": "financial",
                        "keyword_matched": keyword,
                    })
        
        # Calculate confidence score
        total_findings = len(findings["pii"]) + len(findings["phi"]) + len(findings["financial"])
        findings["confidence_score"] = min(total_findings / 10, 1.0)
        
        return findings

    def classify_sensitivity(self, asset: Asset) -> SensitivityLevel:
        """Classify asset sensitivity based on content."""
        findings = self.discover_sensitive_data(asset)
        
        if findings["phi"]:
            return SensitivityLevel.PHI
        elif findings["pii"]:
            return SensitivityLevel.PII
        elif findings["financial"]:
            return SensitivityLevel.CONFIDENTIAL
        else:
            return SensitivityLevel.INTERNAL

    def auto_tag_asset(self, asset: Asset) -> list[str]:
        """Automatically generate tags for an asset."""
        tags = set(asset.tags)
        
        # Add domain-specific tags based on asset name
        name_lower = asset.name.lower()
        
        if any(term in name_lower for term in ["customer", "user", "account"]):
            tags.add("customer_data")
        
        if any(term in name_lower for term in ["transaction", "payment", "order"]):
            tags.add("transactional_data")
        
        if any(term in name_lower for term in ["product", "inventory", "catalog"]):
            tags.add("product_data")
        
        if any(term in name_lower for term in ["employee", "hr", "payroll"]):
            tags.add("hr_data")
        
        if any(term in name_lower for term in ["fact", "metric", "measure"]):
            tags.add("fact_table")
        
        if any(term in name_lower for term in ["dim", "lookup", "reference"]):
            tags.add("dimension_table")
        
        # Add platform tags
        tags.add(asset.platform)
        
        return list(tags)

    def suggest_business_terms(self, asset: Asset) -> list[str]:
        """Suggest business terms for an asset."""
        suggestions = []
        name_lower = asset.name.lower()
        
        # Simple keyword matching for business terms
        term_mappings = {
            "customer": "Customer",
            "user": "User",
            "account": "Account",
            "transaction": "Transaction",
            "order": "Order",
            "product": "Product",
            "invoice": "Invoice",
            "payment": "Payment",
            "employee": "Employee",
            "sales": "Sales",
        }
        
        for keyword, term in term_mappings.items():
            if keyword in name_lower:
                suggestions.append(term)
        
        return suggestions

    def discover_data_products(self) -> list[dict[str, Any]]:
        """Discover potential data products from catalog."""
        assets = self.catalog.list_assets(limit=1000)
        data_products = []
        
        for asset in assets:
            # Heuristic for identifying data products
            if (
                asset.quality_score >= 0.8
                and asset.description
                and any(term in asset.description.lower() for term in ["report", "dashboard", "metric", "kpi"])
            ):
                data_products.append({
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "platform": asset.platform,
                    "quality_score": asset.quality_score,
                    "owner": asset.owner,
                    "domain": asset.domain,
                })
        
        return data_products

    def discover_duplicate_assets(self) -> list[dict[str, Any]]:
        """Discover potentially duplicate assets."""
        assets = self.catalog.list_assets(limit=1000)
        duplicates = []
        
        # Group assets by similar names
        name_groups: dict[str, list[Asset]] = {}
        for asset in assets:
            # Normalize name
            normalized = re.sub(r'[^a-z0-9]', '', asset.name.lower())
            if normalized not in name_groups:
                name_groups[normalized] = []
            name_groups[normalized].append(asset)
        
        # Find groups with multiple assets
        for normalized_name, group in name_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "normalized_name": normalized_name,
                    "assets": [
                        {
                            "id": str(a.id),
                            "name": a.name,
                            "platform": a.platform,
                            "urn": a.urn,
                        }
                        for a in group
                    ],
                })
        
        return duplicates

    def discover_orphaned_assets(self) -> list[dict[str, Any]]:
        """Discover assets with no upstream or downstream dependencies."""
        assets = self.catalog.list_assets(limit=1000)
        orphaned = []
        
        for asset in assets:
            if not asset.upstream_assets and not asset.downstream_assets:
                orphaned.append({
                    "id": str(asset.id),
                    "name": asset.name,
                    "platform": asset.platform,
                    "urn": asset.urn,
                    "suggestion": "Consider adding lineage or deprecating if unused",
                })
        
        return orphaned

    def get_discovery_report(self) -> dict[str, Any]:
        """Generate comprehensive discovery report."""
        assets = self.catalog.list_assets(limit=1000)
        
        report = {
            "total_assets": len(assets),
            "sensitive_assets": 0,
            "pii_assets": 0,
            "phi_assets": 0,
            "orphaned_assets": len(self.discover_orphaned_assets()),
            "duplicate_assets": len(self.discover_duplicate_assets()),
            "data_products": len(self.discover_data_products()),
            "recommendations": [],
        }
        
        for asset in assets:
            findings = self.discover_sensitive_data(asset)
            if findings["pii"] or findings["phi"] or findings["financial"]:
                report["sensitive_assets"] += 1
            if findings["pii"]:
                report["pii_assets"] += 1
            if findings["phi"]:
                report["phi_assets"] += 1
        
        # Add recommendations
        if report["orphaned_assets"] > 0:
            report["recommendations"].append({
                "type": "orphaned_assets",
                "count": report["orphaned_assets"],
                "action": "Review and add lineage or deprecate",
            })
        
        if report["duplicate_assets"] > 0:
            report["recommendations"].append({
                "type": "duplicate_assets",
                "count": report["duplicate_assets"],
                "action": "Consolidate or clarify asset purposes",
            })
        
        return report