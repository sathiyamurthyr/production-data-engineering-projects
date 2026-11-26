"""
================================================================================
MODULE 07: Sets & Fast Deduplication
================================================================================
1. EXPLANATION:
Sets are unordered collections of unique hashable elements. Set lookups occur in O(1) average time,
making them ideal for deduplicating high-volume event data and finding delta diffs between datasets.

2. BUSINESS USE CASE:
Deduplicate incoming CDC event keys and find missing transaction IDs across source and target systems.
"""
from typing import List, Set, Tuple

def reconcile_keys(source_keys: List[str], target_keys: List[str]) -> Tuple[Set[str], Set[str]]:
    """Return missing keys in target and extra keys in target."""
    src_set = set(source_keys)
    tgt_set = set(target_keys)
    missing_in_target = src_set - tgt_set
    extra_in_target = tgt_set - src_set
    return missing_in_target, extra_in_target

if __name__ == "__main__":
    src = ["TXN1", "TXN2", "TXN3", "TXN4"]
    tgt = ["TXN1", "TXN2", "TXN5"]
    missing, extra = reconcile_keys(src, tgt)
    print(f"Missing in Target: {missing}, Extra in Target: {extra}")
