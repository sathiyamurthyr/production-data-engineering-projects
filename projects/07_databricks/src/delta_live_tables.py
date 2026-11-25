"""
Module 05: Delta Live Tables (DLT) — Declarative Pipeline Framework & Expectations
=================================================================================

Explanation:
    Delta Live Tables (DLT) is Databricks' framework for building reliable, maintainable,
    and testable data processing pipelines. DLT manages task orchestration, cluster scale-out,
    error handling, data quality enforcement, and batch/streaming execution automatically.

Business Use Case:
    - Automated ingestion and processing for Medallion architecture (Bronze -> Silver -> Gold).
    - Enterprise data quality enforcement with built-in expectations (WARN, DROP, FAIL).
    - Automated Change Data Capture (CDC) with `dlt.apply_changes` (SCD Type 1 and Type 2).
    - Real-time lineage reporting and data health dashboards.

Architecture:
    +-----------------------+     Expect: drop corrupt      +-----------------------+
    |   Bronze Table (RAW)  |  -------------------------->  | Silver Table (Cleaned)|
    | @dlt.table (AutoLoad) |                               | @dlt.expect_or_drop   |
    +-----------------------+                               +-----------------------+
                                                                        |
                                                            Aggregate   |
                                                                        v
                                                            +-----------------------+
                                                            |  Gold Table (Metrics) |
                                                            |  @dlt.table           |
                                                            +-----------------------+

Performance Notes:
    - DLT automatically optimizes Delta Lake file sizes (Auto Compact & Optimize Write).
    - Pipeline can be run in 'Continuous' (24/7 streaming) or 'Triggered' (batch execution) mode.
    - Enhanced Autoscaling scales workers based on workload queue depth rather than Spark metrics.

Common Mistakes:
    - Mixing raw PySpark DataFrame execution outside `@dlt.table` decorated functions.
    - Using `display()` or `.collect()` inside DLT pipelines (causes execution failure).
    - Missing primary key specification in `dlt.apply_changes` leading to duplicated CDC records.

Interview Questions:
    Q: What are the three data quality expectation modes in Delta Live Tables?
    A: 1. `expect(name, condition)` — logs rule violations to event log without stopping processing.
       2. `expect_or_drop(name, condition)` — drops non-compliant records from the target table.
       3. `expect_or_fail(name, condition)` — halts the entire pipeline run upon violation.

    Q: How does `dlt.apply_changes()` simplify CDC processing?
    A: It handles out-of-order data, primary key deduplication, sequence ordering (by timestamp or offset),
       and automatically maintains SCD Type 1 or Type 2 target tables without complex SQL MERGE statements.
"""

import logging
from typing import Dict, List, Callable, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DLTExpectationMode:
    WARN = "WARN"
    DROP = "DROP"
    FAIL = "FAIL"


class DLTPipelineBuilder:
    """
    Simulation and helper class for defining and validation Delta Live Tables (DLT)
    pipeline schemas, expectations, CDC configurations, and execution metadata.
    """

    def __init__(self, pipeline_name: str, target_schema: str):
        self.pipeline_name = pipeline_name
        self.target_schema = target_schema
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.expectations: Dict[str, List[Dict[str, str]]] = {}

    def register_table(
        self,
        name: str,
        comment: str,
        table_type: str = "TABLE",
        spark_conf: Optional[Dict[str, str]] = None,
    ) -> Callable:
        """
        Decorator simulator for `@dlt.table` or `@dlt.view`.
        """
        def decorator(func: Callable) -> Callable:
            self.tables[name] = {
                "name": name,
                "comment": comment,
                "type": table_type,
                "conf": spark_conf or {},
                "function": func,
            }
            logger.info(f"Registered DLT {table_type}: {name} (Comment: {comment})")
            return func
        return decorator

    def add_expectation(self, table_name: str, constraint_name: str, condition: str, action: str = DLTExpectationMode.WARN):
        """
        Add a quality expectation constraint to a table specification.
        """
        if table_name not in self.expectations:
            self.expectations[table_name] = []

        self.expectations[table_name].append({
            "name": constraint_name,
            "condition": condition,
            "action": action,
        })
        logger.info(f"Added Expectation [{action}] for {table_name}: '{constraint_name}' -> ({condition})")

    def generate_cdc_specification(
        self,
        target_table: str,
        source_table: str,
        keys: List[str],
        sequence_by: str,
        scd_type: int = 1,
        ignore_null_updates: bool = False,
    ) -> Dict[str, Any]:
        """
        Generates standard config dict equivalent to `dlt.apply_changes`.
        """
        cdc_spec = {
            "target": target_table,
            "source": source_table,
            "keys": keys,
            "sequence_by": sequence_by,
            "stored_as_scd_type": f"SCD_TYPE_{scd_type}",
            "ignore_null_updates": ignore_null_updates,
        }
        logger.info(f"Generated CDC Spec for {target_table}: SCD Type {scd_type}")
        return cdc_spec

    def validate_pipeline(self) -> bool:
        """
        Validates that all registered tables have unique names and expectations are well-formed.
        """
        if not self.tables:
            logger.warning("Pipeline validation failed: No tables registered.")
            return False

        for name, spec in self.tables.items():
            if not spec.get("name"):
                logger.error(f"Table validation error: Table missing name spec.")
                return False

        logger.info(f"Pipeline '{self.pipeline_name}' successfully validated with {len(self.tables)} tables.")
        return True


# Production Example Code Pattern for DLT Pipeline Code Representation
def create_sample_dlt_pipeline_definition() -> DLTPipelineBuilder:
    builder = DLTPipelineBuilder("ecommerce_analytics_pipeline", "gold_ecommerce")

    # Bronze layer: raw ingestion
    @builder.register_table("raw_orders_bronze", "Raw orders streaming from cloud storage", "TABLE")
    def raw_orders_bronze():
        # In real DLT: return spark.readStream.format("cloudFiles").option("cloudFiles.format", "json").load(...)
        return "SELECT * FROM raw_json_landing"

    # Silver layer: clean & apply expectations
    @builder.register_table("orders_silver", "Cleaned orders with validated user and order IDs", "TABLE")
    def orders_silver():
        # In real DLT: return dlt.read_stream("raw_orders_bronze").filter(...)
        return "SELECT * FROM dlt.read_stream('raw_orders_bronze')"

    builder.add_expectation("orders_silver", "valid_order_id", "order_id IS NOT NULL", DLTExpectationMode.FAIL)
    builder.add_expectation("orders_silver", "positive_amount", "total_amount > 0", DLTExpectationMode.DROP)

    # Gold layer: business aggregates
    @builder.register_table("daily_revenue_gold", "Daily revenue summary aggregated by country", "TABLE")
    def daily_revenue_gold():
        return "SELECT order_date, country, SUM(total_amount) FROM dlt.read('orders_silver') GROUP BY 1, 2"

    return builder


if __name__ == "__main__":
    logger.info("Initializing DLT Pipeline Builder Demo...")
    pipeline = create_sample_dlt_pipeline_definition()
    pipeline.validate_pipeline()
    cdc_config = pipeline.generate_cdc_specification(
        target_table="dim_customers",
        source_table="customers_cdc_bronze",
        keys=["customer_id"],
        sequence_by="updated_timestamp",
        scd_type=2,
    )
    print("Generated CDC Config:", cdc_config)
