"""Knowledge Graph - Neo4j-based graph implementation."""

from typing import Any

from neo4j import GraphDatabase

from .models import GraphNode, GraphRelationship, EntityType


class KnowledgeGraph:
    """Graph database interface for metadata relationships."""

    def __init__(self, uri: str, user: str, password: str, database: str = "datafabric") -> None:
        """Initialize Neo4j driver."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self._ensure_constraints()

    def _ensure_constraints(self) -> None:
        """Create database constraints."""
        with self.driver.session(database=self.database) as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Column) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Term) REQUIRE t.id IS UNIQUE")

    def create_node(self, node: GraphNode) -> None:
        """Create a node in the graph."""
        with self.driver.session(database=self.database) as session:
            session.run(
                "MERGE (n:" + node.entity_type.value + " {id: $id}) "
                "SET n += $props",
                id=str(node.id),
                props=node.properties,
            )

    def create_relationship(self, relationship: GraphRelationship) -> None:
        """Create a relationship in the graph."""
        with self.driver.session(database=self.database) as session:
            session.run(
                "MATCH (source {id: $source_id}) "
                "MATCH (target {id: $target_id}) "
                "CREATE (source)-[r:" + relationship.type + "]->(target) "
                "SET r += $props",
                source_id=str(relationship.source_id),
                target_id=str(relationship.target_id),
                props=relationship.properties,
            )

    def get_upstream_lineage(self, asset_id: str, depth: int = 5) -> list[GraphNode]:
        """Get upstream lineage for an asset."""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH path = (n:Asset {id: $asset_id})<-[:LINEAGE*1..$depth]-() "
                "RETURN DISTINCT nodes(path) as nodes",
                asset_id=asset_id,
                depth=depth,
            )
            return [GraphNode(**record["nodes"]) for record in result]

    def get_downstream_lineage(self, asset_id: str, depth: int = 5) -> list[GraphNode]:
        """Get downstream lineage for an asset."""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH path = (n:Asset {id: $asset_id})-[:LINEAGE*1..$depth]->() "
                "RETURN DISTINCT nodes(path) as nodes",
                asset_id=asset_id,
                depth=depth,
            )
            return [GraphNode(**record["nodes"]) for record in result]

    def find_similar_assets(self, asset_id: str, limit: int = 10) -> list[GraphNode]:
        """Find similar assets based on shared characteristics."""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (n:Asset {id: $asset_id})-[:SIMILAR_TO]->(similar) "
                "RETURN similar LIMIT $limit",
                asset_id=asset_id,
                limit=limit,
            )
            return [GraphNode(**record["similar"]) for record in result]

    def close(self) -> None:
        """Close the driver connection."""
        self.driver.close()