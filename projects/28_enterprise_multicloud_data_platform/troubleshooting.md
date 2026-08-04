# Multi-Cloud Troubleshooting Handbook

## Table of Contents

1. [Troubleshooting Overview](#troubleshooting-overview)
2. [Common Issues](#common-issues)
3. [Azure Issues](#azure-issues)
4. [AWS Issues](#aws-issues)
5. [Cross-Cloud Connectivity Issues](#cross-cloud-connectivity-issues)
6. [Networking Issues](#networking-issues)
7. [Identity and Access Issues](#identity-and-access-issues)
8. [Data Platform Issues](#data-platform-issues)
9. [AI Platform Issues](#ai-platform-issues)
10. [Performance Issues](#performance-issues)

---

## Troubleshooting Overview

This handbook provides solutions to common issues encountered when operating a multi-cloud data platform. Use this guide to diagnose and resolve problems quickly.

### Troubleshooting Methodology

**1. Identify the Problem**
- Gather symptoms
- Check logs
- Review metrics
- Identify affected services

**2. Diagnose the Root Cause**
- Analyze error messages
- Check dependencies
- Review recent changes
- Test hypotheses

**3. Implement Solution**
- Apply fix
- Test solution
- Monitor results
- Document resolution

**4. Prevent Recurrence**
- Update runbooks
- Add monitoring
- Improve automation
- Train team

---

## Common Issues

### Terraform Issues

**Issue: State Lock Error**
```
Error: Error locking state: Error acquiring the state lock
```

**Solution**
```bash
# Check who has the lock
terraform state list

# Force unlock (use with caution)
terraform force-unlock <lock-id>

# Prevent future locks
# - Use remote backend with locking
# - Avoid concurrent terraform apply
# - Use workspace isolation
```

**Issue: Azure Authentication Failure**
```
Error: Authenticating to Azure CLI
```

**Solution**
```bash
# Re-authenticate
az login

# Set correct subscription
az account set --subscription "plat-data-prod-001"

# Verify service principal
az ad sp show --id <service-principal-id>

# Check token expiry
az account get-access-token
```

**Issue: AWS Authentication Failure**
```
Error: AccessDenied: Access Denied
```

**Solution**
```bash
# Verify credentials
aws sts get-caller-identity

# Re-configure AWS CLI
aws configure

# Check IAM permissions
aws iam get-user

# Verify region
aws configure get region
```

---

## Azure Issues

### AKS Cluster Issues

**Issue: Pods Stuck in Pending State**
```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Common causes:
# 1. Insufficient resources
kubectl get nodes -o wide
kubectl describe node <node-name>

# 2. PVC binding issues
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name>

# 3. Taints and tolerations
kubectl get nodes -o json | jq '.items[].spec.taints'
```

**Solution**
```bash
# Scale node pool
az aks scale \
  --resource-group rg-data-platform-prod-001 \
  --name aks-data-platform-prod-001 \
  --node-count 10

# Check node pool status
az aks nodepool list \
  --resource-group rg-data-platform-prod-001 \
  --cluster-name aks-data-platform-prod-001
```

**Issue: AKS API Server Unreachable**
```bash
# Check API server status
az aks show \
  --resource-group rg-data-platform-prod-001 \
  --name aks-data-platform-prod-001 \
  --query "{fqdn: fqdn, networkProfile: networkProfile}"

# Test connectivity
kubectl cluster-info

# Check firewall rules
az network nsg list \
  --resource-group rg-data-platform-prod-001 \
  --query '[].{name:name, rules:securityRules[?access==`Deny`]}'
```

**Solution**
```bash
# Update firewall rules
az network nsg rule update \
  --resource-group rg-data-platform-prod-001 \
  --nsg-name <nsg-name> \
  --name AllowKubernetesAPI \
  --priority 100 \
  --destination-port-range 443 \
  --access Allow
```

### Azure Storage Issues

**Issue: Storage Account Access Denied**
```bash
# Check storage account firewall
az storage account show \
  --name <storage-account> \
  --resource-group <rg> \
  --query "networkRuleSet"

# Check private endpoint connections
az storage account private-endpoint-connection list \
  --storage-account-name <storage-account> \
  --resource-group <rg>
```

**Solution**
```bash
# Allow trusted services
az storage account update \
  --name <storage-account> \
  --resource-group <rg> \
  --allow-blob-public-access false \
  --public-network-access Enabled

# Add private endpoint
az storage account private-endpoint-connection create \
  --storage-account-name <storage-account> \
  --resource-group <rg> \
  --name <endpoint-name> \
  --subnet <subnet-id>
```

**Issue: Slow Storage Performance**
```bash
# Check metrics
az monitor metrics list \
  --resource <storage-account-id> \
  --metric "SuccessE2ELatency,SuccessServerLatency" \
  --interval PT1H

# Check throttling
az monitor metrics list \
  --resource <storage-account-id> \
  --metric "Ingress, Egress, Transactions" \
  --interval PT1H
```

**Solution**
```bash
# Increase account performance
az storage account update \
  --name <storage-account> \
  --resource-group <rg> \
  --sku Premium_ZRS

# Enable CDN
az cdn endpoint create \
  --resource-group <rg> \
  --profile <cdn-profile> \
  --name <endpoint-name> \
  --origin <storage-account>.blob.core.windows.net
```

### Azure SQL Issues

**Issue: Connection Timeout**
```bash
# Check SQL server firewall
az sql server show \
  --name <sql-server> \
  --resource-group <rg> \
  --query "networkRules"

# Check database status
az sql db show \
  --name <db-name> \
  --server <sql-server> \
  --resource-group <rg> \
  --query "status"
```

**Solution**
```bash
# Allow Azure services
az sql server firewall-rule create \
  --resource-group <rg> \
  --server <sql-server> \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Check connection pool
az sql db show-connection-string \
  --name <db-name> \
  --server <sql-server> \
  --client ado.net
```

---

## AWS Issues

### EKS Cluster Issues

**Issue: Nodes Not Joining Cluster**
```bash
# Check node status
kubectl get nodes

# Describe node
kubectl describe node <node-name>

# Check AWS console
aws eks describe-cluster \
  --name eks-data-platform-prod-001 \
  --region us-east-1 \
  --query "cluster.status"
```

**Solution**
```bash
# Verify IAM role
aws iam get-role --role-name <node-role-name>

# Check security groups
aws ec2 describe-security-groups \
  --group-ids <sg-id>

# Re-join node
kubectl delete node <node-name>
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name <asg-name> \
  --desired-capacity 3
```

**Issue: AWS Load Balancer Not Working**
```bash
# Check load balancer status
aws elb describe-load-balancers \
  --load-balancer-names <lb-name>

# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# Check security groups
aws ec2 describe-security-groups \
  --group-ids <sg-id>
```

**Solution**
```bash
# Verify security group rules
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Check target group
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-path /health
```

### S3 Issues

**Issue: Access Denied to S3 Bucket**
```bash
# Check bucket policy
aws s3 get-bucket-policy \
  --bucket <bucket-name>

# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn <iam-arn> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::<bucket-name>/*
```

**Solution**
```bash
# Update bucket policy
aws s3 put-bucket-policy \
  --bucket <bucket-name> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "<iam-arn>"},
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::<bucket-name>/*"
    }]
  }'
```

**Issue: Slow S3 Performance**
```bash
# Check request metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name AllRequests \
  --dimensions Name=BucketName,Value=<bucket-name> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Check throttling
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name 5xxErrors \
  --dimensions Name=BucketName,Value=<bucket-name> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

**Solution**
```bash
# Enable transfer acceleration
aws s3api put-bucket-accelerate-configuration \
  --bucket <bucket-name> \
  --accelerate-configuration Status=Enabled

# Use CloudFront
aws cloudfront create-distribution \
  --origin-domain-name <bucket-name>.s3.amazonaws.com
```

### RDS Issues

**Issue: High CPU Utilization**
```bash
# Check CPU metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<db-name> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check slow queries
aws rds describe-db-log-files \
  --db-instance-identifier <db-name>
```

**Solution**
```bash
# Scale up instance
aws rds modify-db-instance \
  --db-instance-identifier <db-name> \
  --db-instance-class db.r5.2xlarge \
  --apply-immediately

# Enable Performance Insights
aws rds modify-db-instance \
  --db-instance-identifier <db-name> \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

---

## Cross-Cloud Connectivity Issues

### VPN Issues

**Issue: VPN Tunnel Down**
```bash
# Azure VPN status
az network vpn-connection show \
  --name <connection-name> \
  --resource-group <rg> \
  --query "{status: connectionStatus, ingress: ingressBytesTransferred, egress: egressBytesTransferred}"

# AWS VPN status
aws ec2 describe-vpn-connections \
  --vpn-connection-ids <vpn-id> \
  --query 'VpnConnections[].{Status:VpnTelemetry[].Status}'
```

**Solution**
```bash
# Restart Azure VPN gateway
az network vnet-gateway update \
  --name <gateway-name> \
  --resource-group <rg> \
  --no-wait

# Check BGP status
az network vnet-gateway show \
  --name <gateway-name> \
  --resource-group <rg> \
  --query "bgpSettings"

# Reset VPN tunnel
aws ec2 delete-vpn-connection \
  --vpn-connection-id <vpn-id>
```

### DNS Resolution Issues

**Issue: Cannot Resolve Cross-Cloud Hostnames**
```bash
# Test DNS resolution
nslookup <hostname>
dig <hostname>

# Check DNS zones
# Azure
az network private-dns record-set a list \
  --zone-name <zone-name> \
  --resource-group <rg>

# AWS
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id>
```

**Solution**
```bash
# Verify DNS forwarding
az network vnet-dns-zone show \
  --name <dns-zone> \
  --resource-group <rg>

# Update DNS servers
az network vnet update \
  --name <vnet-name> \
  --resource-group <rg> \
  --dns-servers 168.63.129.16

# Clear DNS cache
systemd-resolve --flush-caches
```

### Network Latency Issues

**Issue: High Latency Between Clouds**
```bash
# Test latency
ping <destination-ip>
traceroute <destination-ip>

# Check network path
mtr <destination-ip>

# Monitor bandwidth
iftop -i <interface>
```

**Solution**
```bash
# Check for congestion
ethtool -S <interface> | grep -i drop

# Optimize routing
# Update route tables with optimal paths
az network route-table route update \
  --resource-group <rg> \
  --name <route-table> \
  --name <route-name> \
  --next-hop-type VirtualNetworkGateway

# Consider ExpressRoute/Direct Connect
```

---

## Identity and Access Issues

### SSO Issues

**Issue: Unable to Authenticate**
```bash
# Check Azure AD status
az ad app show --id <app-id>

# Check SAML configuration
az ad sp show --id <service-principal-id>

# Verify IAM Identity Center
aws ssoadmin list-instances
```

**Solution**
```bash
# Test SAML authentication
curl -v https://login.microsoftonline.com/<tenant>/saml2

# Refresh service principal credentials
az ad sp credential reset \
  --name <app-id> \
  --years 1

# Verify IAM role trust policy
aws iam get-role --role-name <role-name>
```

### RBAC Issues

**Issue: Permission Denied**
```bash
# Check Azure RBAC
az role assignment list \
  --assignee <user-id> \
  --query '[].{Role:roleDefinitionName, Scope:scope}'

# Check AWS IAM
aws iam list-attached-user-policies \
  --user-name <user-name>

aws iam list-user-policies \
  --user-name <user-name>
```

**Solution**
```bash
# Grant Azure RBAC role
az role assignment create \
  --assignee <user-id> \
  --role "Data Engineer" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>

# Update AWS IAM policy
aws iam attach-user-policy \
  --user-name <user-name> \
  --policy-arn <policy-arn>
```

---

## Data Platform Issues

### Kafka Issues

**Issue: Consumer Lag**
```bash
# Check consumer lag
kafka-consumer-groups.sh \
  --bootstrap-server <kafka-server> \
  --describe --group <consumer-group>

# Check topic partitions
kafka-topics.sh \
  --bootstrap-server <kafka-server> \
  --describe --topic <topic-name>
```

**Solution**
```bash
# Increase consumer instances
kubectl scale deployment <consumer-deployment> \
  --replicas=10 \
  -n <namespace>

# Optimize consumer configuration
# - Increase max.poll.records
# - Decrease max.poll.interval.ms
# - Enable auto-commit
```

**Issue: Broker Unavailable**
```bash
# Check broker status
kafka-broker-api-versions.sh \
  --bootstrap-server <kafka-server>

# Check cluster health
kafka-metadata-shell.sh \
  --snapshot-path <path> \
  --mode validate
```

**Solution**
```bash
# Restart broker
kubectl rollout restart statefulset <kafka-broker> \
  -n <namespace>

# Check logs
kubectl logs <broker-pod> -n <namespace> --tail=100
```

### Delta Lake Issues

**Issue: Table Corruption**
```python
# Check Delta table history
spark.sql("DESCRIBE HISTORY delta.`<table-path>`")

# Validate table
spark.sql(f"VALIDATE delta.`{table_path}`")
```

**Solution**
```python
# Restore to previous version
spark.sql(f"RESTORE delta.`{table_path}` TO VERSION AS OF <version>")

# Or vacuum and rebuild
spark.sql(f"VACUUM delta.`{table_path}` RETAIN 168 HOURS")
```

**Issue: Slow Queries**
```python
# Check table statistics
spark.sql(f"ANALYZE TABLE delta.`{table_path}` COMPUTE STATISTICS")

# Optimize table
spark.sql(f"OPTIMIZE delta.`{table_path}`")
```

### Airflow Issues

**Issue: DAG Not Appearing**
```bash
# Check DAG parsing errors
airflow dags list

# Check scheduler logs
kubectl logs -n airflow <scheduler-pod> | grep -i error

# Validate DAG file
airflow dags list --import-error
```

**Solution**
```bash
# Fix DAG syntax
python -m py_compile <dag-file>.py

# Restart scheduler
kubectl rollout restart deployment/airflow-scheduler -n airflow

# Clear DAG errors
airflow dags delete <dag-id>
```

---

## AI Platform Issues

### MLflow Issues

**Issue: MLflow Tracking Server Unavailable**
```bash
# Check MLflow server status
kubectl get pods -n mlflow

# Check logs
kubectl logs -n mlflow <mlflow-pod> --tail=100

# Test connectivity
curl http://<mlflow-service>:5000/health
```

**Solution**
```bash
# Restart MLflow server
kubectl rollout restart deployment/mlflow-server -n mlflow

# Check database connection
kubectl get secret mlflow-secrets -n mlflow -o yaml
```

### Model Serving Issues

**Issue: Model Endpoint Timeout**
```bash
# Check endpoint health
kubectl get endpoints <model-endpoint> -n <namespace>

# Check pod status
kubectl get pods -n <namespace> -l app=<model-service>

# Check logs
kubectl logs -n <namespace> <model-pod> --tail=100
```

**Solution**
```bash
# Scale up replicas
kubectl scale deployment <model-deployment> \
  --replicas=3 \
  -n <namespace>

# Increase resource limits
kubectl patch deployment <model-deployment> \
  -n <namespace> \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"4Gi"}]'
```

---

## Performance Issues

### High CPU Usage

**Diagnosis**
```bash
# Check node metrics
kubectl top nodes

# Check pod metrics
kubectl top pods -n <namespace>

# Azure metrics
az monitor metrics list \
  --resource <vm-id> \
  --metric "Percentage CPU" \
  --interval PT1H

# AWS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solution**
```bash
# Scale horizontally
kubectl scale deployment <deployment> --replicas=5 -n <namespace>

# Scale vertically (Azure)
az vm resize \
  --resource-group <rg> \
  --name <vm-name> \
  --size Standard_D8s_v3

# Scale vertically (AWS)
aws ec2 modify-instance-attribute \
  --instance-id <instance-id> \
  --instance-type "{\"Value\": \"m5.2xlarge\"}"
```

### Memory Issues

**Diagnosis**
```bash
# Check memory usage
kubectl top pods -n <namespace> --sort-by=memory

# Check for OOM kills
kubectl get events -n <namespace> | grep -i oom

# Check node memory
kubectl describe node <node-name> | grep -A 10 "Allocated resources"
```

**Solution**
```bash
# Increase memory limits
kubectl patch deployment <deployment> \
  -n <namespace> \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"8Gi"}]'

# Enable vertical pod autoscaler
kubectl autoscale deployment <deployment> \
  --cpu-max=80 \
  --memory-max=80 \
  -n <namespace>
```

### Disk Space Issues

**Diagnosis**
```bash
# Check disk usage
kubectl exec -n <namespace> <pod-name> -- df -h

# Check persistent volumes
kubectl get pv
kubectl get pvc -n <namespace>
```

**Solution**
```bash
# Expand PVC
kubectl patch pvc <pvc-name> \
  -n <namespace> \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/resources/requests/storage", "value":"500Gi"}]'

# Clean up unused resources
docker system prune -af
kubectl delete completedJobs --all -n <namespace>
```

---

## Monitoring and Debugging

### Enable Debug Logging

**Terraform**
```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform.log
terraform apply
```

**Kubernetes**
```bash
# Enable debug logging for deployment
kubectl patch deployment <deployment> \
  -n <namespace> \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/env/0", "value": {"name": "LOG_LEVEL", "value": "DEBUG"}}]'
```

**Python Applications**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Collect Diagnostic Information

**Support Bundle Script**
```bash
#!/bin/bash
# collect_support_bundle.sh

BUNDLE_DIR="support-bundle-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BUNDLE_DIR

# Kubernetes resources
kubectl get pods -A -o yaml > $BUNDLE_DIR/pods.yaml
kubectl get services -A -o yaml > $BUNDLE_DIR/services.yaml
kubectl get deployments -A -o yaml > $BUNDLE_DIR/deployments.yaml
kubectl get events -A > $BUNDLE_DIR/events.txt

# Logs
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\n"}{end}' | \
while read ns pod; do
  kubectl logs -n $ns $pod --tail=100 > $BUNDLE_DIR/${ns}_${pod}.log 2>&1
done

# Terraform state
terraform show > $BUNDLE_DIR/terraform.state

# Compress
tar -czf $BUNDLE_DIR.tar.gz $BUNDLE_DIR
```

---

## Escalation Procedures

### Severity Levels

**P1 - Critical (RTO < 1 hour)**
- Complete service outage
- Data loss
- Security breach
- Contact: On-call engineer + manager

**P2 - High (RTO < 4 hours)**
- Partial service outage
- Degraded performance
- Contact: On-call engineer

**P3 - Medium (RTO < 24 hours)**
- Non-critical service affected
- Minor bug
- Contact: Team queue

**P4 - Low (RTO < 1 week)**
- Feature request
- Documentation issue
- Contact: GitHub issues

### Escalation Matrix

| Severity | Initial Response | Escalation Time | Escalation Path |
|----------|-----------------|-----------------|-----------------|
| P1 | 15 minutes | 1 hour | On-call → Manager → Director |
| P2 | 30 minutes | 4 hours | On-call → Manager |
| P3 | 4 hours | 24 hours | Team → Manager |
| P4 | 24 hours | 1 week | GitHub → Team |

---

## Best Practices

### Prevention

1. **Monitoring**
   - Set up comprehensive monitoring
   - Configure alerts
   - Review dashboards regularly

2. **Automation**
   - Automate common fixes
   - Implement self-healing
   - Use GitOps for consistency

3. **Testing**
   - Regular DR drills
   - Chaos engineering
   - Load testing

4. **Documentation**
   - Keep runbooks updated
   - Document architecture decisions
   - Share knowledge

### Response

1. **Stay Calm**
   - Follow runbooks
   - Escalate when needed
   - Communicate status

2. **Diagnose Thoroughly**
   - Gather all information
   - Check logs and metrics
   - Identify root cause

3. **Fix Permanently**
   - Address root cause
   - Not just symptoms
   - Prevent recurrence

---

## Useful Commands

### Kubernetes
```bash
# Get all resources
kubectl get all -A

# Describe resource
kubectl describe <resource-type> <name> -n <namespace>

# View logs
kubectl logs <pod-name> -n <namespace> --tail=100

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Port forward
kubectl port-forward <pod-name> 8080:80 -n <namespace>
```

### Azure
```bash
# Check resource status
az resource show --ids <resource-id>

# View activity log
az monitor activity-log list \
  --resource-group <rg> \
  --max-events 50

# Check metrics
az monitor metrics list \
  --resource <resource-id> \
  --metric "Percentage CPU" \
  --interval PT1H
```

### AWS
```bash
# Check resource status
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters <resource-type>

# View CloudTrail
aws cloudtrail lookup-events \
  --max-results 10

# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

---

## Conclusion

Effective troubleshooting requires:
- Systematic approach
- Good monitoring
- Comprehensive runbooks
- Regular practice

Use this handbook as a reference, but always update it with lessons learned from production incidents.