"""
================================================================================
MODULE 14: Safe File Handling & Context Managers
================================================================================
1. EXPLANATION:
File I/O must always use context managers (`with open()`) to ensure file descriptors are closed
immediately after reading/writing, preventing memory and file lock leaks.

2. BUSINESS USE CASE:
Read configuration files or raw log streams line-by-line safely.
"""
from pathlib import Path

def write_and_read_log(file_path: Path, lines: list) -> list:
    """Write lines to file and read them back safely using context managers."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(f"{line}\n")

    read_lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            read_lines.append(line.strip())
    return read_lines

if __name__ == "__main__":
    p = Path("output/test_log.txt")
    res = write_and_read_log(p, ["LOG LINE 1", "LOG LINE 2"])
    print("Read Lines:", res)
