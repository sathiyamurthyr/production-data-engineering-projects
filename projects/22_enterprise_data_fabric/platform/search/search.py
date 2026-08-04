"""Intelligent Search - Enterprise search service for data assets."""

import re
from typing import Any

from ..metadata.models import Asset
from ..catalog.catalog import CatalogService


class SearchService:
    """Enterprise search for data assets."""

    def __init__(self, catalog: CatalogService) -> None:
        """Initialize search service."""
        self.catalog = catalog
        self.search_index: dict[str, list[Asset]] = {}

    def build_search_index(self) -> None:
        """Build search index from catalog."""
        assets = self.catalog.list_assets(limit=10000)
        for asset in assets:
            self._index_asset(asset)

    def _index_asset(self, asset: Asset) -> None:
        """Index an asset for search."""
        # Tokenize asset name and description
        tokens = self._tokenize(f"{asset.name} {asset.description or ''}")
        
        for token in tokens:
            if token not in self.search_index:
                self.search_index[token] = []
            if asset not in self.search_index[token]:
                self.search_index[token].append(asset)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for search."""
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.split(r'[^a-z0-9]+', text)
        return [t for t in tokens if len(t) > 2]

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search for assets matching query."""
        if not self.search_index:
            self.build_search_index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Score assets based on token matches
        scores: dict[Asset, float] = {}
        for token in query_tokens:
            for asset in self.search_index.get(token, []):
                scores[asset] = scores.get(asset, 0) + 1

        # Sort by score and return top results
        ranked_assets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for asset, score in ranked_assets[:limit]:
            results.append({
                "asset": asset,
                "score": score,
                "match_reason": self._get_match_reason(asset, query_tokens),
            })
        
        return results

    def _get_match_reason(self, asset: Asset, query_tokens: list[str]) -> str:
        """Get reason why asset matched query."""
        reasons = []
        
        asset_text = f"{asset.name} {asset.description or ''}".lower()
        for token in query_tokens:
            if token in asset_text:
                reasons.append(f"matched '{token}' in name/description")
        
        for tag in asset.tags:
            if any(token in tag.lower() for token in query_tokens):
                reasons.append(f"matched tag '{tag}'")
                break
        
        for term in asset.glossary_terms:
            if any(token in term.lower() for token in query_tokens):
                reasons.append(f"matched glossary term '{term}'")
                break
        
        return "; ".join(reasons) if reasons else "general match"

    def search_by_type(self, query: str, asset_type: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search for assets of specific type."""
        results = self.search(query, limit=100)
        return [r for r in results if r["asset"].asset_type.value == asset_type][:limit]

    def search_by_platform(self, query: str, platform: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search for assets on specific platform."""
        results = self.search(query, limit=100)
        return [r for r in results if r["asset"].platform == platform][:limit]

    def search_by_domain(self, query: str, domain: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search for assets in specific domain."""
        results = self.search(query, limit=100)
        return [r for r in results if r["asset"].domain == domain][:limit]

    def get_suggestions(self, prefix: str, limit: int = 10) -> list[str]:
        """Get search suggestions for prefix."""
        if not self.search_index:
            self.build_search_index()

        prefix = prefix.lower()
        suggestions = set()
        
        for token in self.search_index.keys():
            if token.startswith(prefix):
                suggestions.add(token)
        
        return sorted(list(suggestions))[:limit]

    def get_popular_searches(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get popular search terms."""
        # In production, track search queries
        return []

    def get_faceted_search(self, query: str) -> dict[str, Any]:
        """Get faceted search results."""
        results = self.search(query, limit=1000)
        
        facets = {
            "platform": {},
            "asset_type": {},
            "domain": {},
            "sensitivity": {},
        }
        
        for result in results:
            asset = result["asset"]
            
            platform = asset.platform
            facets["platform"][platform] = facets["platform"].get(platform, 0) + 1
            
            asset_type = asset.asset_type.value
            facets["asset_type"][asset_type] = facets["asset_type"].get(asset_type, 0) + 1
            
            domain = asset.domain or "unknown"
            facets["domain"][domain] = facets["domain"].get(domain, 0) + 1
            
            sensitivity = asset.sensitivity.value
            facets["sensitivity"][sensitivity] = facets["sensitivity"].get(sensitivity, 0) + 1
        
        return {
            "results": results[:50],
            "facets": facets,
            "total": len(results),
        }