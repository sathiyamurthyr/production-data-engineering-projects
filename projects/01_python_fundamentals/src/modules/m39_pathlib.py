"""
================================================================================
MODULE 39: Pathlib & Object-Oriented Path Management
================================================================================
1. EXPLANATION:
`pathlib.Path` provides object-oriented, cross-platform file path resolution over string path concatenation.

2. BUSINESS USE CASE:
Create directory hierarchies and locate matching data files recursively.
"""
from pathlib import Path

def ensure_directory_structure(base_dir: Path) -> Path:
    """Ensure required pipeline directory subfolder structure exists."""
    output_dir = base_dir / "output" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

if __name__ == "__main__":
    p = ensure_directory_structure(Path("output_test"))
    print("Created Path:", p.resolve())
