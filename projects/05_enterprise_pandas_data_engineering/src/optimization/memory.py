"""
Pandas Memory Optimization

Production patterns for efficient memory usage with large datasets.
"""

import pandas as pd
from typing import Any


def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage.
    
    Converts columns to appropriate dtypes for memory efficiency.
    """
    df_optimized = df.copy()
    
    for col in df_optimized.columns:
        col_type = df_optimized[col].dtype
        
        # Integer optimization
        if col_type in ["int64", "Int64"]:
            df_optimized[col] = pd.to_numeric(
                df_optimized[col], downcast="integer"
            )
        
        # Float optimization
        elif col_type in ["float64", "Float64"]:
            df_optimized[col] = pd.to_numeric(
                df_optimized[col], downcast="float"
            )
        
        # Object to categorical for low cardinality
        elif col_type == "object":
            if df_optimized[col].nunique() / len(df_optimized) < 0.5:
                df_optimized[col] = df_optimized[col].astype("category")
    
    return df_optimized


def get_memory_usage(df: pd.DataFrame) -> dict[str, Any]:
    """Get detailed memory usage statistics."""
    memory_df = df.memory_usage(deep=True)
    total_memory = memory_df.sum()
    
    return {
        "total_bytes": total_memory,
        "total_mb": total_memory / (1024 * 1024),
        "per_column": memory_df.to_dict(),
    }


def process_large_csv_in_chunks(
    filepath: str,
    chunk_size: int = 10000,
    transforms: list[callable] | None = None,
) -> pd.DataFrame:
    """
    Process large CSV files in chunks to avoid memory overflow.
    
    Business Use Case: Billion-row transaction processing.
    """
    chunks = []
    
    for chunk in pd.read_csv(filepath, chunksize=chunk_size):
        if transforms:
            for transform in transforms:
                chunk = transform(chunk)
        
        chunks.append(chunk)
    
    return pd.concat(chunks, ignore_index=True)


def vectorized_string_cleaning(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Clean string columns efficiently using vectorization.
    
    Business Use Case: Customer name standardization.
    """
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            # Vectorized string operations
            df_clean[col] = (
                df_clean[col]
                .str.strip()
                .str.upper()
                .str.replace(r"\s+", " ", regex=True)
            )
    
    return df_clean