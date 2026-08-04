"""REST API Connector - Generic REST API metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class RESTConnector(BaseConnector):
    """Harvest metadata from REST APIs."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize REST connector."""
        super().__init__(config)
        self.platform_name = "rest_api"
        self.base_url = config.get("base_url", "")
        self.auth_type = config.get("auth_type", "bearer")
        self.api_key = config.get("api_key", "")
        self.bearer_token = config.get("bearer_token", "")
        self.headers = config.get("headers", {})

    def test_connection(self) -> bool:
        """Test connection to REST API."""
        try:
            import requests
            response = requests.get(self.base_url, headers=self._get_headers(), timeout=10)
            return response.status_code < 400
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve assets from REST API."""
        assets = []
        try:
            import requests
            endpoints = self.config.get("endpoints", [])
            for endpoint in endpoints:
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self._get_headers(),
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    asset = self._response_to_asset(endpoint, data)
                    assets.append(asset)
        except Exception as e:
            print(f"Error fetching REST assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific asset by ID."""
        try:
            import requests
            endpoint = self.config.get("asset_endpoint", "").format(id=asset_id)
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                return self._response_to_asset(asset_id, data)
        except Exception as e:
            print(f"Error fetching asset {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from REST API."""
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get schema from REST API."""
        return {"properties": {}}

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        headers = {**self.headers}
        if self.auth_type == "bearer" and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.auth_type == "api_key" and self.api_key:
            headers[self.config.get("api_key_header", "X-API-Key")] = self.api_key
        return headers

    def _response_to_asset(self, endpoint: str, data: dict[str, Any]) -> Asset:
        """Convert API response to Asset."""
        return Asset(
            name=data.get("name", endpoint.split("/")[-1]),
            description=data.get("description", f"REST API resource at {endpoint}"),
            asset_type=AssetType.API,
            platform="rest_api",
            platform_id=data.get("id", endpoint),
            domain=self.config.get("domain", "default"),
            tags=["rest", "api"],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata=data,
        )

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST request to API."""
        try:
            import requests
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )
            return response.json() if response.status_code < 400 else {}
        except Exception as e:
            print(f"Error in POST request: {e}")
            return {}

    def put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """PUT request to API."""
        try:
            import requests
            response = requests.put(
                f"{self.base_url}{endpoint}",
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )
            return response.json() if response.status_code < 400 else {}
        except Exception as e:
            print(f"Error in PUT request: {e}")
            return {}

    def delete(self, endpoint: str) -> bool:
        """DELETE request to API."""
        try:
            import requests
            response = requests.delete(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                timeout=30,
            )
            return response.status_code < 400
        except Exception as e:
            print(f"Error in DELETE request: {e}")
            return False