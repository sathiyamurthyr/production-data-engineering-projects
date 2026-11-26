"""
streaming_session.py — Production SparkSession for Structured Streaming
==========================================================================

PURPOSE:
    Central factory for building SparkSession instances configured for
    PySpark Structured Streaming with Kafka integration and Delta Lake support.
    Every streaming application in this project uses this module as its entry
    point so that session configuration is consistent, discoverable, and tested.

BUSINESS USE CASE:
    Production streaming pipelines require careful tuning of:
    - Shuffle partitions (avoid over-partitioning for low-throughput streams)
    - Delta Lake ACID configuration
    - Kafka connector JAR packages
    - Serialization (Kryo for better performance)
    - Adaptive Query Execution (AQE) — disabled for streaming (unsupported)
    - Memory fractions for stateful aggregations

PRODUCTION EXAMPLE:
    from src.streaming_session import StreamingSessionBuilder

    spark = (
        StreamingSessionBuilder("ecommerce-event-pipeline")
        .with_kafka()
        .with_delta_lake()
        .with_streaming_optimizations()
        .build()
    )
    
    # Start reading from Kafka
    df = spark.readStream.format("kafka") ...

PERFORMANCE NOTES:
    - spark.sql.shuffle.partitions: Default 200 is too high for streaming.
      Use 2x the number of Kafka partitions (e.g., 10 Kafka partitions → 20).
    - spark.streaming.stopGracefullyOnShutdown: Ensures micro-batch finishes
      before shutdown, preventing partial writes.
    - spark.databricks.delta.optimizeWrite.enabled: For Databricks, auto-merges
      small files at write time.

INTERVIEW QUESTIONS:
    Q: Why is AQE disabled for Structured Streaming?
    A: AQE (Adaptive Query Execution) changes the physical plan at runtime
       based on statistics. Structured Streaming requires a stable, fixed plan
       across micro-batches to maintain consistency of state. AQE would create
       different plans for different batches, breaking stateful operations.

    Q: What is the purpose of the checkpoint directory in SparkSession config?
    A: Checkpoints store the streaming query's progress (offsets consumed from
       source), the state of stateful operators, and metadata. On failure, Spark
       resumes exactly from the last committed checkpoint, ensuring exactly-once
       or at-least-once processing guarantees depending on sink type.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
import os
from typing import Optional

from pyspark.sql import SparkSession

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — centralise all configuration keys
# ---------------------------------------------------------------------------

# Kryo serialization speeds up shuffle by ~30% over Java serialization
KRYO_SERIALIZER = "org.apache.spark.serializer.KryoSerializer"

# Delta Lake extensions required for streaming ACID writes
DELTA_SQL_EXTENSION = "io.delta.sql.DeltaSparkSessionExtension"
DELTA_CATALOG = "org.apache.spark.sql.delta.catalog.DeltaCatalog"

# Maven coordinates for Spark-Kafka connector (must match Spark and Scala versions)
KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
DELTA_PACKAGE = "io.delta:delta-spark_2.12:3.1.0"


class StreamingSessionBuilder:
    """
    Fluent builder for production SparkSession with Structured Streaming support.

    Usage:
        spark = (
            StreamingSessionBuilder("my-app")
            .with_kafka()
            .with_delta_lake()
            .with_streaming_optimizations(shuffle_partitions=20)
            .with_custom_config("spark.executor.memory", "4g")
            .build()
        )

    Design Rationale:
        - Fluent builder pattern allows composable configuration.
        - Each `.with_*` method is independently optional — callers include only
          what their pipeline needs (e.g., a file-only pipeline skips Kafka).
        - A single build() call applies all configurations, ensuring consistency.
    """

    def __init__(self, app_name: str, master: Optional[str] = None) -> None:
        """
        Initialise the builder with mandatory application name.

        Args:
            app_name: Human-readable name shown in Spark UI and logs.
            master:   Spark master URL. Defaults to SPARK_MASTER env var,
                      then falls back to "local[*]" for local development.
        """
        self.app_name = app_name
        # Prefer environment variable so the same code runs locally and in cluster
        self.master = master or os.getenv("SPARK_MASTER", "local[*]")
        # Internal dict accumulates all spark conf key-value pairs
        self._configs: dict[str, str] = {}
        self._packages: list[str] = []
        self._enable_delta: bool = False
        logger.info("StreamingSessionBuilder initialised: app=%s, master=%s", app_name, self.master)

    # ------------------------------------------------------------------
    # Fluent configuration methods
    # ------------------------------------------------------------------

    def with_kafka(self) -> "StreamingSessionBuilder":
        """
        Add Kafka connector package to the session.

        The spark-sql-kafka connector enables:
            - readStream().format("kafka")  → read from Kafka topics
            - writeStream().format("kafka") → publish results to Kafka topics

        The connector is loaded via Maven at session startup. In production,
        pre-download the JAR and use --jars flag in spark-submit instead of
        --packages to avoid hitting Maven repositories at runtime.
        """
        self._packages.append(KAFKA_PACKAGE)
        logger.debug("Kafka package added: %s", KAFKA_PACKAGE)
        return self

    def with_delta_lake(self) -> "StreamingSessionBuilder":
        """
        Configure Delta Lake extensions for ACID streaming writes.

        Sets:
            spark.sql.extensions       → enables Delta SQL commands (MERGE, DESCRIBE HISTORY)
            spark.sql.catalog.spark_catalog → replaces default catalog with Delta catalog
                                              so Delta tables appear as normal Spark tables.

        Delta Lake streaming benefits:
            - Exactly-once writes via transaction log
            - Schema enforcement on streaming writes
            - Time travel for debugging failed batches
            - OPTIMIZE and VACUUM for file management
        """
        self._enable_delta = True
        self._packages.append(DELTA_PACKAGE)
        self._configs[
            "spark.sql.extensions"
        ] = DELTA_SQL_EXTENSION
        self._configs[
            "spark.sql.catalog.spark_catalog"
        ] = DELTA_CATALOG
        logger.debug("Delta Lake extensions configured")
        return self

    def with_streaming_optimizations(
        self,
        shuffle_partitions: int = 20,
        state_store_memory_mb: int = 512,
    ) -> "StreamingSessionBuilder":
        """
        Apply standard streaming performance tuning.

        Args:
            shuffle_partitions:   Number of shuffle partitions. Rule of thumb:
                                  2x the number of Kafka partitions per topic.
                                  Default 200 kills performance on small streams.
            state_store_memory_mb: Memory in MB for RocksDB or in-memory state store.
                                   Increase for pipelines with large stateful windows
                                   (e.g., 30-minute session windows with millions of users).

        Why disable AQE for streaming?
            Adaptive Query Execution (AQE) modifies the query plan based on
            runtime statistics collected after each shuffle. In streaming, the
            plan must remain identical across micro-batches to avoid breaking
            stateful aggregation operators that depend on consistent state layout.
        """
        configs = {
            # Tune partitions for streaming: avoids 200 tiny tasks per micro-batch
            "spark.sql.shuffle.partitions": str(shuffle_partitions),
            # CRITICAL: disable AQE — it changes plans mid-stream, breaking state
            "spark.sql.adaptive.enabled": "false",
            # Kryo serializer: ~30% faster than Java serializer for shuffle data
            "spark.serializer": KRYO_SERIALIZER,
            # Register common Spark types with Kryo for even faster serialization
            "spark.kryo.registrationRequired": "false",
            # Allow Spark to finish the current micro-batch before shutting down
            # Prevents partial writes and data loss on SIGTERM
            "spark.streaming.stopGracefullyOnShutdown": "true",
            # RocksDB state store handles large state without GC pressure
            # Switch to "RocksDB" for stateful aggregations over long windows
            "spark.sql.streaming.stateStore.providerClass": (
                "org.apache.spark.sql.execution.streaming.state.HDFSBackedStateStoreProvider"
            ),
            # State store memory limit
            "spark.sql.streaming.statefulOperator.stateStore.memoryLimit": (
                f"{state_store_memory_mb}m"
            ),
            # Fetch offset range per micro-batch from Kafka to control throughput
            "spark.sql.streaming.kafka.useDeprecatedOffsetFetching": "false",
        }
        self._configs.update(configs)
        logger.debug("Streaming optimizations applied: shuffle_partitions=%d", shuffle_partitions)
        return self

    def with_checkpoint_location(self, base_path: str) -> "StreamingSessionBuilder":
        """
        Set a default checkpoint directory for all streaming queries.

        Individual queries can override this via writeStream.option("checkpointLocation", ...)
        This global setting acts as a fallback for queries that don't specify their own.

        Args:
            base_path: Base HDFS / S3 / ADLS / DBFS path for checkpoints.
                       Each query will create a sub-directory under this path.
        """
        self._configs["spark.sql.streaming.checkpointLocation"] = base_path
        logger.debug("Checkpoint base path set: %s", base_path)
        return self

    def with_custom_config(self, key: str, value: str) -> "StreamingSessionBuilder":
        """
        Add any arbitrary Spark configuration key-value pair.

        Use this for environment-specific configs not covered by the named methods,
        such as cloud storage credentials, Hive metastore URI, or custom timeouts.

        Args:
            key:   Full Spark configuration key (e.g., "spark.executor.memory").
            value: Configuration value as string.
        """
        self._configs[key] = value
        return self

    def build(self) -> SparkSession:
        """
        Construct and return the configured SparkSession.

        If a SparkSession already exists (e.g., in Databricks notebooks where
        Spark is pre-initialised), returns the existing session. This prevents
        "Cannot have two SparkContexts" errors in interactive environments.

        Returns:
            SparkSession: Fully configured session ready for streaming.
        """
        # Start building session
        builder = (
            SparkSession.builder
            .appName(self.app_name)
            .master(self.master)
        )

        # Apply all accumulated configuration
        for key, value in self._configs.items():
            builder = builder.config(key, value)

        # If packages are specified, join them as comma-separated string
        # (spark.jars.packages is a comma-delimited list)
        if self._packages:
            packages_str = ",".join(self._packages)
            builder = builder.config("spark.jars.packages", packages_str)
            logger.info("Spark packages: %s", packages_str)

        # getOrCreate: safe for both fresh starts and existing sessions (Databricks)
        spark = builder.getOrCreate()

        # Set log level to WARN to suppress INFO-level Spark noise in production logs
        spark.sparkContext.setLogLevel("WARN")

        logger.info(
            "SparkSession built: app=%s, version=%s, delta=%s",
            spark.conf.get("spark.app.name"),
            spark.version,
            self._enable_delta,
        )
        return spark


# ---------------------------------------------------------------------------
# Convenience factory functions for common pipeline configurations
# ---------------------------------------------------------------------------

def create_kafka_delta_session(
    app_name: str,
    checkpoint_base: Optional[str] = None,
    shuffle_partitions: int = 20,
) -> SparkSession:
    """
    Create a SparkSession configured for the most common production pattern:
    Kafka source → Structured Streaming → Delta Lake sink.

    This is the recommended entry point for the majority of streaming pipelines
    in this project that don't need custom session configuration.

    Args:
        app_name:           Application name for Spark UI and log correlation.
        checkpoint_base:    Base path for checkpoint directories.
                            Reads from CHECKPOINT_BASE_PATH env var if not provided.
        shuffle_partitions: Number of shuffle partitions (default 20 for streaming).

    Returns:
        Fully configured SparkSession.

    Example:
        spark = create_kafka_delta_session(
            "order-events-pipeline",
            checkpoint_base="/mnt/checkpoints",
        )
    """
    checkpoint_base = checkpoint_base or os.getenv(
        "CHECKPOINT_BASE_PATH", "/tmp/streaming_checkpoints"
    )
    return (
        StreamingSessionBuilder(app_name)
        .with_kafka()
        .with_delta_lake()
        .with_streaming_optimizations(shuffle_partitions=shuffle_partitions)
        .with_checkpoint_location(checkpoint_base)
        .build()
    )


def create_test_session(app_name: str = "streaming-test") -> SparkSession:
    """
    Create a lightweight SparkSession for unit and integration testing.

    Differences from production session:
    - local[2] master: uses only 2 threads to keep tests fast
    - No Kafka/Delta packages (not needed for in-memory test sinks)
    - Minimal shuffle partitions for fast test execution
    - AQE disabled to ensure deterministic query plans

    Args:
        app_name: Test session name.

    Returns:
        Minimal SparkSession suitable for pytest fixtures.

    Example (conftest.py):
        @pytest.fixture(scope="session")
        def spark():
            session = create_test_session()
            yield session
            session.stop()
    """
    return (
        StreamingSessionBuilder(app_name, master="local[2]")
        .with_streaming_optimizations(shuffle_partitions=4)
        .build()
    )


def get_or_create_session(app_name: str) -> SparkSession:
    """
    Return the active SparkSession if one exists, otherwise create a new one.

    Useful in module-level code that may be called from both:
    - Standalone scripts (need to create session)
    - Interactive notebooks / Databricks (session already exists)

    Args:
        app_name: Application name used only when creating a new session.

    Returns:
        Active SparkSession.
    """
    existing = SparkSession.getActiveSession()
    if existing is not None:
        logger.info("Reusing existing SparkSession: %s", existing.conf.get("spark.app.name"))
        return existing

    logger.info("No active session found, creating new session: %s", app_name)
    return create_kafka_delta_session(app_name)


# ---------------------------------------------------------------------------
# Entry point — demonstrates session creation and basic streaming info
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    spark = create_kafka_delta_session(
        app_name="streaming-demo",
        checkpoint_base="/tmp/demo_checkpoints",
        shuffle_partitions=8,
    )

    print("\n=== SparkSession Configuration ===")
    print(f"App Name          : {spark.conf.get('spark.app.name')}")
    print(f"Spark Version     : {spark.version}")
    print(f"Master            : {spark.conf.get('spark.master')}")
    print(f"Shuffle Partitions: {spark.conf.get('spark.sql.shuffle.partitions')}")
    print(f"Serializer        : {spark.conf.get('spark.serializer')}")
    print(f"Delta Extension   : {spark.conf.get('spark.sql.extensions', 'not set')}")

    # Verify streaming is available by checking the streaming context
    active_streams = spark.streams.active
    print(f"\nActive Streaming Queries: {len(active_streams)}")
    print("Session ready for streaming. No active queries yet.")

    spark.stop()
