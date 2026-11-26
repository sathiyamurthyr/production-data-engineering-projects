"""SQLite-backed Knowledge Graph store with RDFS/OWL-lite reasoning and traversal."""

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from src.models import GraphEdge, GraphNode
from src.schema.ontology_registry import OntologyRegistry, OntologyValidationError


class KnowledgeGraphStore:
    """Persists schema-validated ontology instances, relationships, and inferred triples."""

    def __init__(self, db_path: str | Path, registry: OntologyRegistry) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = registry
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    uri TEXT PRIMARY KEY,
                    class_name TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_edges (
                    subject_uri TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_uri TEXT NOT NULL,
                    inferred INTEGER NOT NULL DEFAULT 0,
                    properties_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (subject_uri, predicate, object_uri)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_nodes_class ON kg_nodes(class_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_subj ON kg_edges(subject_uri)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_obj ON kg_edges(object_uri)")
            conn.commit()

    def upsert_node(
        self,
        class_name: str,
        pk_value: str,
        properties: Dict[str, Any],
        source_system: str = "pipeline",
    ) -> GraphNode:
        """Validate properties against OntologyRegistry and atomically upsert node."""
        validated = self.registry.validate_instance(class_name, properties)
        uri = self.registry.make_uri(class_name, pk_value)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kg_nodes (uri, class_name, properties_json, source_system, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    class_name = excluded.class_name,
                    properties_json = excluded.properties_json,
                    source_system = excluded.source_system,
                    updated_at = excluded.updated_at
                """,
                (uri, class_name, json.dumps(validated), source_system, now),
            )
            conn.commit()
        return GraphNode(
            uri=uri,
            class_name=class_name,
            properties=validated,
            source_system=source_system,
        )

    def get_node(self, uri: str) -> Optional[GraphNode]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT uri, class_name, properties_json, source_system FROM kg_nodes WHERE uri = ?",
                (uri,),
            ).fetchone()
        if not row:
            return None
        return GraphNode(
            uri=row[0],
            class_name=row[1],
            properties=json.loads(row[2]),
            source_system=row[3],
        )

    def add_edge(
        self,
        subject_uri: str,
        predicate: str,
        object_uri: str,
        properties: Optional[Dict[str, Any]] = None,
        materialize_inverse: bool = True,
    ) -> GraphEdge:
        """Validate domain/range compatibility and persist edge + optional inverse edge."""
        subj = self.get_node(subject_uri)
        obj = self.get_node(object_uri)
        if subj is None:
            raise OntologyValidationError(f"Unknown subject node URI: {subject_uri}")
        if obj is None:
            raise OntologyValidationError(f"Unknown object node URI: {object_uri}")

        rspec = self.registry.validate_relationship(predicate, subj.class_name, obj.class_name)
        edge_props = properties or {}
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kg_edges (subject_uri, predicate, object_uri, inferred, properties_json, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                ON CONFLICT(subject_uri, predicate, object_uri) DO UPDATE SET
                    inferred = 0,
                    properties_json = excluded.properties_json,
                    updated_at = excluded.updated_at
                """,
                (subject_uri, predicate, object_uri, json.dumps(edge_props), now),
            )
            if materialize_inverse and rspec.inverse:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO kg_edges
                        (subject_uri, predicate, object_uri, inferred, properties_json, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                    """,
                    (object_uri, rspec.inverse, subject_uri, json.dumps(edge_props), now),
                )
            conn.commit()

        return GraphEdge(
            subject_uri=subject_uri,
            predicate=predicate,
            object_uri=object_uri,
            inferred=False,
            properties=edge_props,
        )

    def materialize_transitive_closures(self) -> int:
        """Compute and persist transitive closure edges (and inverses) for transitive predicates."""
        inferred_added = 0
        now = datetime.now(timezone.utc).isoformat()

        for predicate, rspec in self.registry.relationships.items():
            if not rspec.transitive:
                continue

            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT subject_uri, object_uri FROM kg_edges WHERE predicate = ?",
                    (predicate,),
                ).fetchall()

            adj: Dict[str, Set[str]] = {}
            for s, o in rows:
                adj.setdefault(s, set()).add(o)

            existing_pairs = set(rows)
            new_pairs: List[Tuple[str, str]] = []

            for start in adj:
                visited: Set[str] = set()
                queue = deque(adj.get(start, ()))
                while queue:
                    curr = queue.popleft()
                    if curr in visited or curr == start:
                        continue
                    visited.add(curr)
                    if (start, curr) not in existing_pairs:
                        new_pairs.append((start, curr))
                    for nxt in adj.get(curr, ()):
                        if nxt not in visited:
                            queue.append(nxt)

            if new_pairs:
                with self._connect() as conn:
                    for s, o in new_pairs:
                        cur = conn.execute(
                            """
                            INSERT OR IGNORE INTO kg_edges
                                (subject_uri, predicate, object_uri, inferred, properties_json, updated_at)
                            VALUES (?, ?, ?, 1, '{}', ?)
                            """,
                            (s, predicate, o, now),
                        )
                        inferred_added += cur.rowcount
                        if rspec.inverse:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO kg_edges
                                    (subject_uri, predicate, object_uri, inferred, properties_json, updated_at)
                                VALUES (?, ?, ?, 1, '{}', ?)
                                """,
                                (o, rspec.inverse, s, now),
                            )
                    conn.commit()

        return inferred_added

    def query_instances(self, class_name: str, include_subclasses: bool = True) -> List[GraphNode]:
        """Retrieve all instances of class_name, optionally expanding subclasses via ontology."""
        if class_name not in self.registry.classes:
            raise OntologyValidationError(f"Unknown ontology class: '{class_name}'")

        target_classes = (
            self.registry.get_subclasses(class_name, include_self=True)
            if include_subclasses
            else [class_name]
        )
        placeholders = ",".join("?" for _ in target_classes)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT uri, class_name, properties_json, source_system FROM kg_nodes "
                f"WHERE class_name IN ({placeholders}) ORDER BY uri",
                tuple(target_classes),
            ).fetchall()

        return [
            GraphNode(
                uri=row[0],
                class_name=row[1],
                properties=json.loads(row[2]),
                source_system=row[3],
            )
            for row in rows
        ]

    def get_edges(
        self,
        subject_uri: Optional[str] = None,
        predicate: Optional[str] = None,
        object_uri: Optional[str] = None,
        include_inferred: bool = True,
    ) -> List[GraphEdge]:
        clauses: List[str] = []
        params: List[Any] = []
        if subject_uri is not None:
            clauses.append("subject_uri = ?")
            params.append(subject_uri)
        if predicate is not None:
            clauses.append("predicate = ?")
            params.append(predicate)
        if object_uri is not None:
            clauses.append("object_uri = ?")
            params.append(object_uri)
        if not include_inferred:
            clauses.append("inferred = 0")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT subject_uri, predicate, object_uri, inferred, properties_json "
                f"FROM kg_edges {where} ORDER BY subject_uri, predicate, object_uri",
                tuple(params),
            ).fetchall()

        return [
            GraphEdge(
                subject_uri=row[0],
                predicate=row[1],
                object_uri=row[2],
                inferred=bool(row[3]),
                properties=json.loads(row[4]),
            )
            for row in rows
        ]

    def list_all_nodes(self) -> List[GraphNode]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT uri, class_name, properties_json, source_system FROM kg_nodes ORDER BY uri"
            ).fetchall()
        return [
            GraphNode(uri=r[0], class_name=r[1], properties=json.loads(r[2]), source_system=r[3])
            for r in rows
        ]

    def find_shortest_path(self, start_uri: str, end_uri: str) -> Optional[List[GraphEdge]]:
        """BFS shortest path across directed edges (including materialized inverses)."""
        if start_uri == end_uri:
            return []
        visited: Set[str] = {start_uri}
        queue: deque[Tuple[str, List[GraphEdge]]] = deque([(start_uri, [])])
        while queue:
            curr, path = queue.popleft()
            for edge in self.get_edges(subject_uri=curr, include_inferred=True):
                if edge.object_uri == end_uri:
                    return path + [edge]
                if edge.object_uri not in visited:
                    visited.add(edge.object_uri)
                    queue.append((edge.object_uri, path + [edge]))
        return None

    def extract_subgraph(
        self, root_uri: str, max_hops: int = 2
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract N-hop neighborhood nodes and edges around root_uri for GraphRAG."""
        root = self.get_node(root_uri)
        if root is None:
            return [], []

        visited: Set[str] = {root_uri}
        frontier: deque[Tuple[str, int]] = deque([(root_uri, 0)])
        collected_edges: List[GraphEdge] = []
        seen_edge_keys: Set[Tuple[str, str, str]] = set()

        while frontier:
            curr_uri, depth = frontier.popleft()
            if depth >= max_hops:
                continue
            for edge in self.get_edges(subject_uri=curr_uri, include_inferred=True):
                key = (edge.subject_uri, edge.predicate, edge.object_uri)
                if key not in seen_edge_keys:
                    seen_edge_keys.add(key)
                    collected_edges.append(edge)
                if edge.object_uri not in visited:
                    visited.add(edge.object_uri)
                    frontier.append((edge.object_uri, depth + 1))

        nodes = [node for uri in sorted(visited) if (node := self.get_node(uri)) is not None]
        return nodes, collected_edges
