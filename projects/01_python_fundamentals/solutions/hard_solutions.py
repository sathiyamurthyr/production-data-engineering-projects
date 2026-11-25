"""Solution for Hard Level Exercises."""
import json
from pathlib import Path
from typing import Generator, List, Dict, Any

def microbatch_file_reader(file_path: Path, batch_size: int = 2) -> Generator[List[Dict[str, Any]], None, None]:
    batch = []
    if not file_path.exists():
        return
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                batch.append(data)
                if len(batch) == batch_size:
                    yield batch
                    batch = []
            except json.JSONDecodeError:
                continue
        if batch:
            yield batch
