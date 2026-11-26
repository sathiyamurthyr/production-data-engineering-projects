# Troubleshooting Runbook

## 1. `OntologyValidationError: Subject class 'Order' is not compatible with domain 'Customer'`
- **Cause:** Edge direction was inverted (`add_edge(order_uri, "PLACED_ORDER", customer_uri)`).
- **Fix:** Check `domain` and `range` in `configs/ontology_schema.yaml` (`Customer -> PLACED_ORDER -> Order`).

## 2. `OntologyValidationError: Cannot instantiate abstract class 'LegalEntity'`
- **Cause:** Code attempted `upsert_node("LegalEntity", ...)`.
- **Fix:** Instantiate concrete subclasses (`Customer` or `Merchant`) instead; query `LegalEntity` via `query_instances("LegalEntity", include_subclasses=True)`.

## 3. Duplicate Customer Nodes Created for the Same User
- **Cause:** Source records differed in email casing or middle initials (`aarav.sharma@example.com` vs `AARAV.SHARMA@example.com`).
- **Fix:** Route raw CRM feeds through `CustomerEntityResolver.resolve_customers()` before `upsert_node()`.

## 4. Transitive Parent Links Missing After Ingestion
- **Cause:** `add_edge()` added direct `SUBSIDIARY_OF` links, but `materialize_transitive_closures()` was not invoked.
- **Fix:** Always run `graph.materialize_transitive_closures()` after loading hierarchical edges (handled automatically by `OntologyIngestionPipeline.run()`).
