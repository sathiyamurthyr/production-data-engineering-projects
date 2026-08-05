# Security Policy

## Supported Versions

All patterns in this repository are maintained with security in mind. We follow
secure coding practices and regularly review for vulnerabilities.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue,
please report it responsibly.

**Do NOT open a public GitHub issue.**

Instead, report to: **rsm.sathiyam@gmail.com**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a fix within 7 days.

## Security Standards

All patterns must follow:
- OWASP Top 10 for data applications
- Principle of least privilege
- Zero-trust architecture principles
- Encryption at rest and in transit
- Secure credential management
- PII detection and protection
- Access logging and audit trails

## Security Checklist for Contributions

- [ ] No hardcoded secrets or credentials
- [ ] Secrets managed via environment variables or secret managers
- [ ] PII data is masked or tokenized
- [ ] Access controls are implemented
- [ ] Encryption is used for data at rest and in transit
- [ ] Audit logging is included
- [ ] No sensitive data in test fixtures