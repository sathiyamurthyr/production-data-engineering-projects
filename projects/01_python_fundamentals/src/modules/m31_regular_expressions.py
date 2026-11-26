"""
================================================================================
MODULE 31: Regular Expressions for PII Redaction
================================================================================
1. EXPLANATION:
Regex identifies patterns in raw log files or text payloads for PII masking (emails, credit card numbers).

2. BUSINESS USE CASE:
Mask email addresses in customer log strings prior to cloud storage ingestion.
"""
import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def mask_email(text: str) -> str:
    """Replace emails with '[REDACTED]'."""
    return EMAIL_REGEX.sub("[REDACTED]", text)

if __name__ == "__main__":
    msg = "User contact is alice@example.com for order 100."
    print("Masked Message:", mask_email(msg))
