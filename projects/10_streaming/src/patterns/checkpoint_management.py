"""
checkpoint_management.py — Checkpoint Storage & Stream Recovery Management
=============================================================================

PURPOSE:
    Provides management patterns for streaming query checkpoints in PySpark Structured Streaming.
    Checkpoints store stateful operational metadata:
    1. Offset Log: Tracks precise source offsets (e.g. Kafka partition offset ranges) processed in each micro-batch.
    2. Commit Log: Records successfully committed micro-batches to destination sinks.
    3. StateStore Delta Files: In-memory or RocksDB state snapshots required for stateful window aggregations.
    4. Metadata: Stream query ID and run schema definition.

BUSINESS USE CASE:
    - Pipeline Failure Recovery: When a cluster node fails or spot instance terminates, restarting the streaming job uses the checkpoint to resume execution from the exact offset without data loss or duplication.
    - Zero-Downtime Code Upgrades: Code updates (that retain compatible schemas) read existing checkpoints to resume state.

CHECKPOINT DIRECTORY STRUCTURE:
    ```
    /checkpoint_dir/
    ├── offsets/      ← Micro-batch source offset metadata (e.g., 0, 1, 2, 3...)
    ├── commits/      ← Micro-batch sink commit confirmation logs
    ├── state/        ← StateStore delta snapshots for windowed aggregations
    └── metadata      ← Streaming query metadata and schema GUID
    ```

INTERVIEW QUESTIONS:
    Q: What happens if you change the DataFrame schema of a stateful streaming query and restart from an existing checkpoint?
    A: Incompatible schema changes (e.g. altering column types or removing stateful key fields) cause a `StateSchemaNotCompatibleException`. For incompatible schema changes, you must point the job to a NEW checkpoint directory (which resets stream state).

    Q: Can two concurrent streaming queries share the same checkpoint directory?
    A: NEVER! Sharing a checkpoint directory causes state corruption and offset collision failures. Every streaming query MUST have its own unique checkpoint path.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
import os
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Utility for managing streaming query checkpoint directories.
    """

    def __init__(self, base_dir: str = "/tmp/streaming_checkpoints") -> None:
        """
        Initialise CheckpointManager.

        Args:
            base_dir: Root storage directory for streaming checkpoints.
        """
        self.base_dir = base_dir

    def get_query_checkpoint_dir(self, query_name: str) -> str:
        """
        Construct and return formatted checkpoint path for a named streaming query.

        Args:
            query_name: Unique query identifier.

        Returns:
            Absolute checkpoint path directory string.
        """
        clean_name = query_name.lower().replace(" ", "_")
        path = os.path.join(self.base_dir, clean_name)
        logger.debug("Resolved checkpoint path for '%s': %s", query_name, path)
        return path

    def purge_checkpoint(self, query_name: str) -> bool:
        """
        Delete checkpoint directory for a specific query (forcing cold start).

        WARNING: Use only in non-production environments or backfill re-ingestion scenarios!

        Args:
            query_name: Name of query checkpoint to purge.

        Returns:
            True if deleted successfully, False if directory did not exist.
        """
        path = self.get_query_checkpoint_dir(query_name)
        if os.path.exists(path):
            logger.warning("PURGING streaming checkpoint path: %s", path)
            shutil.rmtree(path)
            return True
        logger.info("No checkpoint directory found to purge at: %s", path)
        return False

    def verify_checkpoint_exists(self, query_name: str) -> bool:
        """
        Check if a valid checkpoint directory exists for a query.

        Args:
            query_name: Streaming query identifier name.

        Returns:
            True if checkpoint folder and offsets log exist.
        """
        path = self.get_query_checkpoint_dir(query_name)
        offsets_path = os.path.join(path, "offsets")
        exists = os.path.exists(offsets_path)
        logger.info("Checkpoint status for '%s': exists=%s", query_name, exists)
        return exists


def resolve_checkpoint_location(
    query_name: str,
    base_path: str = "/tmp/checkpoints",
    purge_existing: bool = False,
) -> str:
    """
    Helper function to resolve or reset checkpoint directory.

    Args:
        query_name: Name of streaming query.
        base_path: Base directory path.
        purge_existing: If True, purges existing checkpoint before starting.

    Returns:
        Checkpoint path string.
    """
    manager = CheckpointManager(base_dir=base_path)
    if purge_existing:
        manager.purge_checkpoint(query_name)
    return manager.get_query_checkpoint_dir(query_name)
