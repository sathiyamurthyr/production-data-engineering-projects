"""
================================================================================
MODULE 26: Strict Type Hinting & Static Type Checking
================================================================================
1. EXPLANATION:
Type hints (`typing.List`, `Dict`, `Optional`, `Union`, `Callable`) allow static verification via MyPy.

2. BUSINESS USE CASE:
Type-annotate custom transformation pipelines.
"""
from typing import List, Dict, Optional, Union

def process_optional_records(
    records: List[Dict[str, Union[str, float]]], limit: Optional[int] = None
) -> List[Dict[str, Union[str, float]]]:
    if limit is not None:
        return records[:limit]
    return records
