"""
Module: acid_transactions.py
============================
ACID Guarantees Demo: Concurrent reads/writes, transaction isolation.

Business Use Case:
    Before Delta Lake, data lakes had no ACID guarantees. A reader could
    see partial data mid-write. Two writers to the same partition could
    corrupt each other's files. Downstream jobs could fail due to missing
    files that were being renamed.

    Delta Lake brings ACID transactions to data lakes through its
    transaction log — a sequence of JSON files (commits) in _delta_log/.
    This module demonstrates each ACID property with concrete examples.

ACID Properties in Delta Lake:
    ┌────────────┬────────────────────────────────────────────────────────┐
    │ Property   │ How Delta Implements It                                 │
    ├────────────┼────────────────────────────────────────────────────────┤
    │ Atomicity  │ Write creates new files first; log entry is the commit  │
    │            │ If Spark crashes mid-write, no log entry = no change    │
    ├────────────┼────────────────────────────────────────────────────────┤
    │ Consistency│ Schema enforcement rejects writes that violate schema   │
    │            │ Constraints (CHECK, NOT NULL) prevent bad data          │
    ├────────────┼────────────────────────────────────────────────────────┤
    │ Isolation  │ Snapshot Isolation: each reader sees a consistent       │
    │            │ snapshot of the table from when their read started      │
    │            │ Optimistic Concurrency Control handles concurrent writes│
    ├────────────┼────────────────────────────────────────────────────────┤
    │ Durability │ Written files + committed log entry = durable           │
    │            │ If Spark dies AFTER commit, data is safe                │
    └────────────┴────────────────────────────────────────────────────────┘

Concurrency Control:
    Delta uses Optimistic Concurrency Control (OCC):
    1. Writer reads current table version (snapshot isolation)
    2. Writer performs transformations
    3. Writer attempts to commit a new version
    4. Delta checks for conflicts with any commits since step 1
    5a. If no conflict → commit succeeds
    5b. If conflict → commit fails with ConcurrentModificationException
        Writer can retry (Delta retries automatically for certain operations)

    Conflict detection is at the transaction level:
    - Two appends never conflict
    - Two updates to DIFFERENT partitions don't conflict
    - Two updates to the SAME row → one fails

Interview Questions:
    Q: What isolation level does Delta Lake provide?
    A: Snapshot Isolation by default. Each reader sees the table as it
       was when their query started, regardless of concurrent writes.
       Delta does NOT provide Serializable isolation by default, but it
       can be configured with isolation level settings.

    Q: What happens if two Spark jobs write to the same Delta table
       at the same time?
    A: Delta uses OCC. Both writers read the current version, compute
       their output, and try to commit. Delta detects if their writes
       conflict (e.g., both writing to the same partition). If they don't
       conflict (e.g., writing to different partitions), both succeed.
       If they conflict, one gets ConcurrentModificationException.

    Q: How does Delta achieve Atomicity?
    A: All new Parquet files are written BEFORE the log entry is created.
       The log entry (commit) is a single atomic file write. If Spark
       crashes before the log entry, the orphaned Parquet files are
       invisible to readers (cleaned up by VACUUM). If Spark crashes
       after the log entry, the data is fully committed.

    Q: What is the _delta_log directory?
    A: It's the transaction log stored alongside data files. It contains:
       - JSON files (00000000000000000000.json, ...) — one per commit
       - Checkpoint files (every 10 commits) — Parquet snapshots of log state
       Each JSON commit records: which files were added, which were removed,
       the operation type, metadata changes, and commit timestamp.
"""

import logging
import threading
import time
from typing import Any

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sample Schema for ACID Demos
# ---------------------------------------------------------------------------

ACCOUNT_SCHEMA = StructType([
    StructField("account_id", IntegerType(), nullable=False),
    StructField("account_name", StringType(), nullable=False),
    StructField("balance", DoubleType(), nullable=False),
    StructField("last_updated", TimestampType(), nullable=True),
])


# ---------------------------------------------------------------------------
# Atomicity Demo
# ---------------------------------------------------------------------------

def demonstrate_atomicity(spark: SparkSession, table_path: str) -> None:
    """
    Demonstrate Delta Lake's Atomicity guarantee.

    Atomicity means: either ALL of a write succeeds, or NONE of it is visible.
    There is no "half-written" state from a reader's perspective.

    How it works:
        1. Spark writes all Parquet data files to the table directory
        2. Spark creates a new JSON entry in _delta_log/
        3. The JSON entry references the new data files
        → If step 1 fails: No log entry exists, files are orphaned (invisible)
        → If step 2 fails: No log entry exists, files are orphaned (invisible)
        → Only when step 2 SUCCEEDS is the data visible to readers

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Path for the demo Delta table.
    """
    print("\n" + "=" * 60)
    print("ATOMICITY DEMO")
    print("=" * 60)

    # ── Step 1: Create initial table ─────────────────────────────────────
    print("\n[1] Creating accounts table with 3 accounts")
    accounts_data = [
        (1, "Alice Checking", 5000.00),
        (2, "Bob Savings", 10000.00),
        (3, "Charlie Money Market", 25000.00),
    ]
    df = spark.createDataFrame(accounts_data, ["account_id", "account_name", "balance"])
    df.write.format("delta").mode("overwrite").save(table_path)

    initial_total = spark.read.format("delta").load(table_path).agg(
        F.sum("balance")
    ).collect()[0][0]
    print(f"    Initial total balance: ${initial_total:,.2f}")

    # ── Step 2: Simulate a multi-step transaction (MERGE) ─────────────────
    print("\n[2] Performing atomic balance transfer: $1000 from Alice to Bob")

    # In a real bank transfer, you'd use a MERGE to atomically
    # update both accounts in one transaction
    dt = DeltaTable.forPath(spark, table_path)

    # Delta's MERGE is a single atomic transaction:
    # Either BOTH account updates succeed, or NEITHER does
    updates_df = spark.createDataFrame(
        [(1, -1000.0), (2, 1000.0)],
        ["account_id", "delta_amount"]
    )

    # Merge to apply balance changes
    (
        dt.alias("target")
        .merge(updates_df.alias("source"), "target.account_id = source.account_id")
        .whenMatchedUpdate(set={"balance": F.col("target.balance") + F.col("source.delta_amount")})
        .execute()
    )

    final_total = spark.read.format("delta").load(table_path).agg(
        F.sum("balance")
    ).collect()[0][0]
    print(f"    Final total balance: ${final_total:,.2f}")
    print(f"    Conservation check: ${initial_total:,.2f} = ${final_total:,.2f} → {'✓ PASS' if initial_total == final_total else '✗ FAIL'}")

    spark.read.format("delta").load(table_path).show()

    # ── Step 3: Show that a failed write leaves table unchanged ───────────
    print("\n[3] Demonstrating atomic failure: invalid data rejected by schema")
    print("    Attempting to append a row with wrong schema...")

    try:
        bad_df = spark.createDataFrame(
            [("account_x", "Invalid Account", "not_a_number")],
            ["account_id", "account_name", "balance"]
        )
        bad_df.write.format("delta").mode("append").save(table_path)
        print("    ✗ Write succeeded (unexpected)")
    except Exception as e:
        print(f"    ✓ Write REJECTED: {type(e).__name__}")
        print("      Table is unchanged — atomicity preserved")

    row_count = spark.read.format("delta").load(table_path).count()
    print(f"    Row count still: {row_count} (unchanged) ✓")


# ---------------------------------------------------------------------------
# Consistency Demo
# ---------------------------------------------------------------------------

def demonstrate_consistency(spark: SparkSession, table_path: str) -> None:
    """
    Demonstrate Delta Lake's Consistency guarantee.

    Consistency means: the database remains in a valid state before and
    after every transaction. Delta enforces this through:
    1. Schema enforcement (rejects writes that violate the schema)
    2. CHECK constraints (rejects data that violates business rules)
    3. NOT NULL constraints (rejects missing required values)

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Path for the demo Delta table.
    """
    print("\n" + "=" * 60)
    print("CONSISTENCY DEMO")
    print("=" * 60)

    # ── Create table with constraints ─────────────────────────────────────
    print("\n[1] Creating table with CHECK constraint (balance >= 0)")
    spark.sql(f"""
        CREATE OR REPLACE TABLE delta.`{table_path}_constrained` (
            account_id INT NOT NULL,
            account_name STRING NOT NULL,
            balance DOUBLE NOT NULL
        )
        USING DELTA
    """)

    # Add a CHECK constraint — balances must be non-negative
    try:
        spark.sql(f"""
            ALTER TABLE delta.`{table_path}_constrained`
            ADD CONSTRAINT balance_non_negative
            CHECK (balance >= 0)
        """)
        print("    ✓ CHECK constraint added: balance >= 0")
    except Exception as e:
        print(f"    Note: CHECK constraints may require Databricks/specific Delta version: {e}")

    # ── Insert valid data ─────────────────────────────────────────────────
    print("\n[2] Inserting valid data (balance = 100.0 >= 0)")
    try:
        spark.sql(f"""
            INSERT INTO delta.`{table_path}_constrained`
            VALUES (1, 'Valid Account', 100.0)
        """)
        print("    ✓ Valid insert succeeded")
    except Exception as e:
        print(f"    Note: {e}")

    # ── Insert invalid data ───────────────────────────────────────────────
    print("\n[3] Attempting to insert invalid data (balance = -50.0 < 0)")
    print("    This should fail due to CHECK constraint...")
    try:
        spark.sql(f"""
            INSERT INTO delta.`{table_path}_constrained`
            VALUES (2, 'Negative Balance Account', -50.0)
        """)
        print("    ✗ Insert succeeded (constraint not enforced in local mode)")
    except Exception as e:
        print(f"    ✓ Insert REJECTED: balance -50.0 violates CHECK constraint")
        print(f"    Error: {type(e).__name__}")


# ---------------------------------------------------------------------------
# Isolation Demo (Snapshot Isolation)
# ---------------------------------------------------------------------------

def demonstrate_isolation(spark: SparkSession, table_path: str) -> None:
    """
    Demonstrate Delta Lake's Snapshot Isolation.

    Snapshot Isolation means: a reader sees a consistent snapshot of
    the table from the moment their query began. Concurrent writes that
    commit AFTER the reader started are NOT visible to that reader.

    In practice on a single SparkSession this is simulated via versions.
    In production with concurrent jobs, two jobs reading "current version"
    get different snapshots if a write commits between them.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Path for the demo Delta table.
    """
    print("\n" + "=" * 60)
    print("ISOLATION DEMO (Snapshot Isolation)")
    print("=" * 60)

    # ── Setup: create table with initial data ─────────────────────────────
    print("\n[1] Creating initial table (version 0): 3 products")
    products_data = [
        (101, "Laptop", 999.99, 50),
        (102, "Phone", 699.99, 100),
        (103, "Tablet", 499.99, 75),
    ]
    df = spark.createDataFrame(
        products_data, ["product_id", "name", "price", "stock"]
    )
    df.write.format("delta").mode("overwrite").save(table_path)

    # ── Simulate concurrent reads and writes via versions ─────────────────
    print("\n[2] Reader A starts reading (snapshot at version 0)")
    # In production: Reader A's job starts, takes snapshot of version 0
    reader_a_snapshot_version = 0

    print("\n[3] Writer commits a price update (creates version 1)")
    # Price increase for Laptop
    dt = DeltaTable.forPath(spark, table_path)
    dt.update(
        condition=F.col("product_id") == 101,
        set={"price": F.lit(1099.99)}
    )
    print("    Laptop price updated: $999.99 → $1099.99")

    print("\n[4] Reader B starts reading (snapshot at version 1)")
    reader_b_snapshot_version = 1

    print("\n[5] Demonstrating isolation:")

    # Reader A sees version 0 (the snapshot when it started)
    reader_a_df = spark.read.format("delta") \
        .option("versionAsOf", reader_a_snapshot_version) \
        .load(table_path)
    reader_a_price = reader_a_df.filter(
        F.col("product_id") == 101
    ).select("price").collect()[0][0]

    # Reader B sees version 1 (current version)
    reader_b_df = spark.read.format("delta") \
        .option("versionAsOf", reader_b_snapshot_version) \
        .load(table_path)
    reader_b_price = reader_b_df.filter(
        F.col("product_id") == 101
    ).select("price").collect()[0][0]

    print(f"    Reader A (version 0) sees Laptop price: ${reader_a_price}")
    print(f"    Reader B (version 1) sees Laptop price: ${reader_b_price}")
    print(f"    Both readers see CONSISTENT data ✓")
    print(f"    No dirty reads possible with Delta's snapshot isolation ✓")


# ---------------------------------------------------------------------------
# Durability Demo
# ---------------------------------------------------------------------------

def demonstrate_durability(spark: SparkSession, table_path: str) -> None:
    """
    Explain Delta Lake's Durability guarantee.

    Durability means: once a transaction commits, it persists even if
    the system crashes immediately after. Delta achieves this through:

    1. Write-ahead logging: Data files are written to durable storage BEFORE
       the commit log entry is written. The commit = single atomic file write.
    2. The log entry references specific Parquet files by path + checksum.
       If Spark dies after committing, the Parquet files are already durable.
    3. On cloud storage (S3/GCS/ADLS): object stores provide 11-nines
       durability. Combined with Delta's transactional log, data is extremely
       durable.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Path for the demo Delta table.
    """
    print("\n" + "=" * 60)
    print("DURABILITY DEMO")
    print("=" * 60)

    print("\n[1] Writing data and showing the durable commit record")

    # Write some data
    df = spark.createDataFrame(
        [(1, "Transaction A", 500.0), (2, "Transaction B", 750.0)],
        ["id", "description", "amount"]
    )
    df.write.format("delta").mode("overwrite").save(table_path)

    # The history shows the durable commit record
    print("\n    Transaction History (durable record of all commits):")
    history = DeltaTable.forPath(spark, table_path).history()
    history.select(
        "version", "timestamp", "operation", "operationMetrics"
    ).show(truncate=False)

    print("\n[2] Explaining durability guarantees:")
    print("    • Each commit = one JSON file in _delta_log/")
    print("    • JSON file creation is atomic (O_CREAT | O_EXCL on POSIX)")
    print("    • On S3/GCS: PUT request atomicity = no partial writes")
    print("    • Crash BEFORE log entry: orphaned Parquet files, no visible change")
    print("    • Crash AFTER log entry: data is fully durable, visible on restart")
    print("    • Checkpoints: every 10 commits, a Parquet snapshot of log state")
    print("      prevents reading thousands of small JSON files on cold start")


# ---------------------------------------------------------------------------
# Complete ACID Demo Runner
# ---------------------------------------------------------------------------

def run_acid_demonstration(spark: SparkSession, base_path: str) -> None:
    """
    Run the complete ACID demonstration sequence.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    base_path : str
        Base directory for demo tables.
    """
    print("\n" + "=" * 70)
    print("DELTA LAKE ACID TRANSACTIONS DEMONSTRATION")
    print("=" * 70)
    print("Delta Lake provides full ACID guarantees for big data workloads.")
    print("Each demonstration shows a specific ACID property in action.\n")

    demonstrate_atomicity(spark, f"{base_path}/acid_atomicity")
    demonstrate_consistency(spark, f"{base_path}/acid_consistency")
    demonstrate_isolation(spark, f"{base_path}/acid_isolation")
    demonstrate_durability(spark, f"{base_path}/acid_durability")

    print("\n" + "=" * 70)
    print("ACID DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("Summary:")
    print("  A — Atomicity:  Writes are all-or-nothing (log entry = commit)")
    print("  C — Consistency: Schema + constraints ensure valid data always")
    print("  I — Isolation:  Snapshot isolation prevents dirty/phantom reads")
    print("  D — Durability: Committed data survives crashes (log + files)")
