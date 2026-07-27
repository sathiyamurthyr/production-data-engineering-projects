"""
ThreadPoolExecutor for Data Engineering

Production patterns for concurrent data processing.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable
import pandas as pd


def parallel_csv_processing(
    filepaths: list[str],
    processor: Callable[[pd.DataFrame], pd.DataFrame],
    max_workers: int = 4,
) -> pd.DataFrame:
    """
    Process multiple CSV files in parallel.
    
    Business Use Case: Monthly sales data from multiple regions.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(pd.read_csv, fp): fp
            for fp in filepaths
        }

        for future in as_completed(futures):
            df = processor(future.result())
            results.append(df)

    return pd.concat(results, ignore_index=True)


def parallel_api_calls(
    urls: list[str],
    fetch_func: Callable[[str], dict[str, Any]],
    max_workers: int = 10,
) -> list[dict[str, Any]]:
    """
    Make parallel API calls using thread pool.
    
    Business Use Case: Concurrent API ingestion for ETL.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_func, url): url for url in urls}

        for future in as_completed(futures):
            results.append(future.result())

    return results


def chunk_parallel_processing(
    data: pd.DataFrame,
    func: Callable[[pd.DataFrame], pd.DataFrame],
    chunk_size: int = 1000,
    max_workers: int = 4,
) -> pd.DataFrame:
    """
    Process large DataFrame in chunks using thread pool.
    
    Business Use Case: Billion-row transaction processing.
    """
    chunks = [
        data[i : i + chunk_size]
        for i in range(0, len(data), chunk_size)
    ]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, chunk) for chunk in chunks]

        results = [future.result() for future in as_completed(futures)]

    return pd.concat(results, ignore_index=True)