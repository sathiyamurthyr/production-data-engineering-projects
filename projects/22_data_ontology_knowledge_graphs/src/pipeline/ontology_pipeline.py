"""End-to-end Ontology mapping, entity resolution, and Knowledge Graph pipeline."""

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Optional
import yaml

from src.graph.knowledge_graph import KnowledgeGraphStore
from src.mapping.entity_resolver import CustomerEntityResolver
from src.schema.ontology_registry import OntologyRegistry


@dataclass(frozen=True)
class OntologyPipelineReport:
    """Execution telemetry for one Knowledge Graph build run."""

    customers_raw: int
    customers_resolved: int
    merchants_loaded: int
    products_loaded: int
    orders_loaded: int
    payments_loaded: int
    explicit_edges: int
    inferred_edges_added: int
    total_nodes: int
    total_edges: int


class OntologyIngestionPipeline:
    """Maps heterogeneous CRM, catalog, and order feeds into a validated Knowledge Graph."""

    def __init__(
        self,
        registry: OntologyRegistry,
        graph_db_path: str | Path,
    ) -> None:
        self.registry = registry
        self.resolver = CustomerEntityResolver(namespace=registry.namespace)
        self.graph = KnowledgeGraphStore(graph_db_path, registry)

    @classmethod
    def from_yaml(
        cls, schema_path: str | Path, graph_db_path: Optional[str | Path] = None
    ) -> "OntologyIngestionPipeline":
        path = Path(schema_path)
        with path.open("r", encoding="utf-8") as handle:
            raw_cfg = yaml.safe_load(handle)
        registry = OntologyRegistry.from_dict(raw_cfg)
        storage_path = graph_db_path or (
            path.parent.parent / raw_cfg.get("storage", {}).get("graph_db_path", "output/kg.sqlite")
        )
        return cls(registry=registry, graph_db_path=storage_path)

    def run(self, data_dir: str | Path) -> OntologyPipelineReport:
        root = Path(data_dir)
        explicit_edges = 0

        # 1. Resolve & load Customers
        with (root / "crm_customers.csv").open("r", encoding="utf-8", newline="") as f:
            raw_customers = list(csv.DictReader(f))
        resolved_customers = self.resolver.resolve_customers(raw_customers)
        email_to_uri: Dict[str, str] = {}
        for cust in resolved_customers:
            node = self.graph.upsert_node(
                "Customer", cust.canonical_id, cust.properties, source_system="crm"
            )
            email_to_uri[cust.properties["email"]] = node.uri

        # 2. Load Merchants & corporate ownership links
        with (root / "merchant_accounts.csv").open("r", encoding="utf-8", newline="") as f:
            merchant_rows = list(csv.DictReader(f))
        for row in merchant_rows:
            self.graph.upsert_node(
                "Merchant",
                row["merchant_id"],
                {
                    "entity_id": row["merchant_id"],
                    "display_name": row["merchant_name"],
                    "mcc_code": row["mcc_code"],
                    "risk_rating": row["risk_rating"],
                    "country": row["country"],
                },
                source_system="merchant_master",
            )
        for row in merchant_rows:
            parent_id = (row.get("parent_merchant_id") or "").strip()
            if parent_id:
                child_uri = self.registry.make_uri("Merchant", row["merchant_id"])
                parent_uri = self.registry.make_uri("Merchant", parent_id)
                self.graph.add_edge(child_uri, "SUBSIDIARY_OF", parent_uri)
                explicit_edges += 1

        # 3. Load Products & SOLD_BY links
        products_loaded = 0
        with (root / "products.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                p_node = self.graph.upsert_node(
                    "Product",
                    rec["sku_id"],
                    {
                        "sku_id": rec["sku_id"],
                        "name": rec["name"],
                        "category": rec["category"],
                        "unit_price": float(rec["unit_price"]),
                    },
                    source_system="catalog",
                )
                m_uri = self.registry.make_uri("Merchant", rec["merchant_id"])
                self.graph.add_edge(p_node.uri, "SOLD_BY", m_uri)
                explicit_edges += 1
                products_loaded += 1

        # 4. Load Orders, PaymentTransactions, and Customer/Product/Payment links
        orders_loaded = 0
        payments_loaded = 0
        with (root / "orders.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                o_node = self.graph.upsert_node(
                    "Order",
                    rec["order_id"],
                    {
                        "order_id": rec["order_id"],
                        "total_amount": float(rec["total_amount"]),
                        "status": rec["status"],
                        "order_date": rec["order_date"],
                    },
                    source_system="orders_oms",
                )
                orders_loaded += 1

                cust_uri = email_to_uri[rec["customer_email"].strip().lower()]
                self.graph.add_edge(cust_uri, "PLACED_ORDER", o_node.uri)
                explicit_edges += 1

                for sku_id in rec["sku_ids"]:
                    p_uri = self.registry.make_uri("Product", sku_id)
                    self.graph.add_edge(o_node.uri, "CONTAINS_PRODUCT", p_uri)
                    explicit_edges += 1

                t_node = self.graph.upsert_node(
                    "PaymentTransaction",
                    rec["txn_id"],
                    {
                        "txn_id": rec["txn_id"],
                        "amount": float(rec["total_amount"]),
                        "rail": rec["rail"],
                        "status": rec["txn_status"],
                    },
                    source_system="payments_gateway",
                )
                payments_loaded += 1
                self.graph.add_edge(o_node.uri, "SETTLED_BY", t_node.uri)
                explicit_edges += 1

        # 5. Materialize transitive & inverse reasoning
        inferred_added = self.graph.materialize_transitive_closures()
        all_nodes = self.graph.list_all_nodes()
        all_edges = self.graph.get_edges(include_inferred=True)

        return OntologyPipelineReport(
            customers_raw=len(raw_customers),
            customers_resolved=len(resolved_customers),
            merchants_loaded=len(merchant_rows),
            products_loaded=products_loaded,
            orders_loaded=orders_loaded,
            payments_loaded=payments_loaded,
            explicit_edges=explicit_edges,
            inferred_edges_added=inferred_added,
            total_nodes=len(all_nodes),
            total_edges=len(all_edges),
        )
