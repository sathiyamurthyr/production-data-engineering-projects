# Security Platform Troubleshooting Guide

## Quick Diagnostics

```bash
# Check platform health
curl https://security.example.com/health

# View logs
kubectl logs -n security-system -l app=security-api --tail=100

# Check authentication service
kubectl logs -n security-system -l app=auth-service --tail=100
```

## Common Issues

### Authentication Failures

**Invalid credentials**: Verify user exists, check password policy
```bash
platform users reset-password <username>
```

**Token expired**: Refresh token or re-authenticate
```bash
platform login --username user@example.com
```

### Authorization Issues

**Access denied**: Check RBAC/ABAC policies
```bash
platform auth permissions <user-id>
platform policies evaluate <resource-id>
```

### Encryption Issues

**Decryption failures**: Verify key access
```bash
platform keys verify <key-id>
platform encryption status
```

### Compliance Violations

**Policy violations**: Review and remediate
```bash
platform compliance violations --framework GDPR
platform compliance remediate <violation-id>
```

## Getting Help

```bash
# Collect debug info
platform debug collect --output security-debug.tar.gz

# Support: security-support@example.com
```

## References

- [Architecture](architecture.md)
- [Zero Trust Guide](zero-trust.md)
- [Incident Response](incident-response.md)