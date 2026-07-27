"""
Delta Lake Writer for Enterprise Data Engineering

Production patterns for ACID-compliant writes.
"""

from typing import Any


def write_delta_table(
    df: Any,
    path: str,
    mode: str = "overwrite",
    partition_by: str | None = None,
) -> Any:
    """
    Write DataFrame to Delta table.
    
    Business Use Case: Bronze to Silver layer ingestion.
    """
    return df.write.format("delta").mode(mode).save(path)


def merge_delta_table(
    df: Any,
    target_path: str,
    merge_condition: str,
    when_matched: str = "update",
) -> Any:
    """
    MERGE operation on Delta table.
    
    Business Use Case: SCD Type 2 updates.
    """
    from delta.tables import DeltaTable

    delta_table = DeltaTable.forPath(df.sparkSession, target_path)

    if when_matched == "update":
        return delta_table.alias("target").merge(
            df.alias("source"),
            merge_condition,
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

    return delta_table


def write_with_schema_enforcement(
    df: Any,
    path: str,
    schema: Any,
) -> Any:
    """
    Write with schema validation.
    
    Business Use Case: Data quality enforcement.
    """
    return (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "false")
        .schema(schema)
        .save(path)
    )