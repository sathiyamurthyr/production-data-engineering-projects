"""
Module 31, 37-40: Regular Expressions, CLI Arguments, OS, Pathlib, and Subprocess.

Explanation:
- Pathlib: Cross-platform object-oriented file path operations.
- Regex: Masking sensitive PII (credit cards, emails, SSN) before writing to lakehouse.
- Subprocess: Triggering external CLI tools (e.g. spark-submit, dbt run).

Business Use Case:
Sanitize logs with Regex, inspect directory structures with Pathlib, and check system readiness.
"""

import re
from pathlib import Path
from typing import List

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

def sanitize_pii(text: str) -> str:
    """Mask email addresses in raw log messages for GDPR compliance."""
    return EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

def find_files_by_extension(directory: Path, extension: str) -> List[Path]:
    """Locate all matching files recursively using Pathlib."""
    if not directory.exists():
        return []
    return list(directory.glob(f"**/*.{extension.lstrip('.')}"))
