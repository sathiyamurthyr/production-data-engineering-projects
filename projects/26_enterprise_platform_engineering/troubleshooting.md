# Troubleshooting Guide

## Platform Health Checks

```bash
# Check platform status
curl https://platform.example.com/health

# Check API
curl https://platform.example.com/api/v1/health

# View logs
kubectl logs -n platform-system -l app=platform-api --tail=100
kubectl logs -n platform-system -l app=platform-worker --tail=100
```

## Common Issues

### Authentication Problems

**Invalid credentials**: Verify username/password, check SSO config, reset password
```bash
platform users reset-password <username>
```

**Token expired**: Refresh token or re-login
```bash
platform login --username user@example.com
```

### Provisioning Issues

**Stuck in validating**: Check policy violations, fix variables, cancel and retry
```bash
platform logs <request-id>
platform cancel <request-id>
```

**Policy violation**: Review policies, update configuration
```bash
platform policies get <policy-id>
```

**Terraform fails**: Check Azure credentials, permissions, quotas
```bash
az account show
terraform plan -var-file=environments/dev.tfvars
```

### Template Issues

**Template not found**: Verify name, check if published
```bash
platform templates list --all
```

**Validation fails**: Check variable schema
```bash
platform templates schema <template-id>
platform templates validate <template-id> --var-file vars.yaml
```

### Kubernetes Issues

**Pods pending**: Check resources, PVC, node selectors
```bash
kubectl describe pod <pod-name> -n platform-system
kubectl get pvc -n platform-system
```

**Services can't connect**: Check NetworkPolicies, DNS
```bash
kubectl get networkpolicy -n platform-system
kubectl exec -n platform-system <pod> -- nslookup <service>
```

### Database Issues

**Connection failures**: Verify DB running, connection string, credentials
```bash
kubectl get pods -n platform-system -l app=postgres
kubectl logs -n platform-system <postgres-pod>
```

**Performance**: Check slow queries, add indexes
```sql
SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

## Performance Issues

**Slow API**: Scale pods, enable caching, optimize queries
```bash
kubectl scale deployment/platform-api -n platform-system --replicas=5
```

**High memory**: Increase limits, check for leaks
```bash
kubectl top pods -n platform-system
kubectl patch deployment platform-api -n platform-system -p '{"spec": {"template": {"spec": {"containers": [{"name": "api", "resources": {"limits": {"memory": "2Gi"}}}]}}}}'
```

## Network Issues

**External access**: Check ingress, DNS, load balancer
```bash
kubectl get ingress -n platform-system
kubectl get svc -n ingress-nginx
```

**SSL errors**: Verify cert-manager, ClusterIssuer
```bash
kubectl get certificates -n platform-system
kubectl describe certificate <cert-name> -n platform-system
```

## Getting Help

```bash
# Collect debug info
platform debug collect --output debug.tar.gz

# Support channels
# Slack: #platform-support
# Email: platform-support@example.com
# Docs: https://docs.platform.example.com