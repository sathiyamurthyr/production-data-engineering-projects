"""Solution for Easy Level Exercises."""
from typing import List

def clean_emails(raw_emails: List[str]) -> List[str]:
    """Clean and filter raw emails."""
    cleaned = []
    for email in raw_emails:
        s = email.strip().lower()
        if "@" in s and "." in s.split("@")[-1]:
            cleaned.append(s)
    return cleaned
