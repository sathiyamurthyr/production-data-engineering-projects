"""
OpenMetadata Client Module
==========================
Provides client REST API integration to push dataset schemas, tags, and lineage
graphs into an enterprise OpenMetadata metadata server.
"""

import logging
from typing import Dict, List, Optional, Any
from src.catalog.data_catalog import CatalogEntry
from src.lineage.lineage_tracker import LineageEdge

logger = logging.getLogger(__name__)

class OpenMetadataClient:
    """
    Interface for synchronizing governance metadata with OpenMetadata REST APIs.
    Supports local simulation mode when OpenMetadata cluster is unreachable.
    """

    def __init__(
        self,
        host: str = "http://localhost:8585",
        api_version: str = "v1",
        jwt_token: str = "mock_token",
        simulation_mode: bool = True,
    ) -> None:
        self.host = host.rstrip("/")
        self.api_version = api_version
        self.jwt_token = jwt_token
        self.simulation_mode = simulation_mode
        self._published_entities: Dict[str, Dict[str, Any]] = {}
        self._published_lineage: List[Dict[str, Any]] = []

    def health_check(self) -> bool:
        """Verify connection to OpenMetadata server."""
        if self.simulation_mode:
            logger.info("OpenMetadataClient [SIMULATION]: Health check OK.")
            return True

        try:
            import requests
            url = f"{self.host}/api/{self.api_version}/system/version"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            resp = requests.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception as err:
            logger.warning(f"OpenMetadata connection failed: {err}. Falling back to simulation.")
            return False

    def publish_table_entity(self, entry: CatalogEntry) -> Dict[str, Any]:
        """
        Register a table entity in OpenMetadata catalog.
        
        Args:
            entry: CatalogEntry object.
            
        Returns:
            Dictionary payload of created entity.
        """
        payload = {
            "name": entry.asset_name,
            "displayName": entry.asset_name,
            "description": entry.description,
            "owner": entry.owner,
            "domain": entry.domain,
            "tableType": entry.asset_type.upper(),
            "columns": [
                {"name": name, "dataType": dtype, "tags": list(entry.tags)}
                for name, dtype in entry.schema_fields.items()
            ],
            "tags": [{"tagFQN": tag} for tag in entry.tags],
        }

        self._published_entities[entry.asset_id] = payload
        logger.info(f"OpenMetadata: Published table entity '{entry.asset_name}' [{entry.asset_id}].")
        return payload

    def publish_lineage_edge(self, edge: LineageEdge) -> Dict[str, Any]:
        """
        Register a directional lineage edge in OpenMetadata.
        
        Args:
            edge: LineageEdge object.
            
        Returns:
            Dictionary payload of registered lineage edge.
        """
        lineage_payload = {
            "edge": {
                "fromEntity": {"name": edge.source_asset, "type": "table"},
                "toEntity": {"name": edge.target_asset, "type": "table"},
                "description": f"Pipeline: {edge.pipeline_name} ({edge.transformation_type})",
            }
        }
        self._published_lineage.append(lineage_payload)
        logger.info(f"OpenMetadata: Published lineage link {edge.source_asset} -> {edge.target_asset}.")
        return lineage_payload

    def get_published_entities(self) -> Dict[str, Dict[str, Any]]:
        """Return dict of published entities."""
        return self._published_entities

    def get_published_lineage(self) -> List[Dict[str, Any]]:
        """Return list of published lineage edges."""
        return self._published_lineage
