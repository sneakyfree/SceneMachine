# SceneMachine Kubernetes Deployment

This directory contains Kubernetes manifests for deploying SceneMachine to a Kubernetes cluster.

## Structure

```
k8s/
├── base/                    # Base manifests (shared across environments)
│   ├── kustomization.yaml   # Kustomize configuration
│   ├── namespace.yaml       # Namespace definition
│   ├── configmap.yaml       # Application configuration
│   ├── secrets.yaml         # Secrets template (DO NOT commit real values)
│   ├── backend-deployment.yaml    # Backend API deployment
│   ├── postgres-statefulset.yaml  # PostgreSQL StatefulSet
│   ├── redis-deployment.yaml      # Redis deployment
│   ├── pvc.yaml             # Persistent Volume Claims
│   ├── ingress.yaml         # Ingress + Network Policy
│   ├── hpa.yaml             # Horizontal Pod Autoscaler + PDBs
│   └── backup-cronjob.yaml  # Database backup jobs
├── overlays/
│   ├── staging/             # Staging environment overrides
│   │   └── kustomization.yaml
│   └── production/          # Production environment overrides
│       ├── kustomization.yaml
│       └── resources.yaml   # Resource limits and quotas
└── monitoring/              # Monitoring stack
    ├── kustomization.yaml
    ├── prometheus.yaml      # Prometheus deployment + alerts
    └── grafana.yaml         # Grafana deployment + dashboards
```

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- kustomize (or kubectl with kustomize support)
- NGINX Ingress Controller
- cert-manager (for TLS)
- Storage class named `standard`

## Quick Start

### 1. Create Secrets

Before deploying, create a secrets file with real values:

```bash
# Copy template
cp k8s/base/secrets.yaml k8s/secrets-real.yaml

# Edit with real values (base64 encoded)
# NEVER commit this file
```

### 2. Deploy to Staging

```bash
# Preview what will be deployed
kubectl kustomize k8s/overlays/staging

# Apply to cluster
kubectl apply -k k8s/overlays/staging
```

### 3. Deploy to Production

```bash
# Preview
kubectl kustomize k8s/overlays/production

# Apply
kubectl apply -k k8s/overlays/production
```

### 4. Deploy Monitoring

```bash
kubectl apply -k k8s/monitoring
```

## Environment Differences

| Setting | Staging | Production |
|---------|---------|------------|
| Backend Replicas | 1 | 3 |
| Max Replicas (HPA) | 3 | 10 |
| Backend Memory | 512Mi-2Gi | 1Gi-4Gi |
| DB Storage | 20Gi | 100Gi |
| Uploads Storage | 50Gi | 100Gi |
| Outputs Storage | 100Gi | 500Gi |
| Log Level | DEBUG | INFO |
| Analytics | Disabled | Enabled |

## Monitoring

### Access Grafana

```bash
# Port forward to local machine
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open http://localhost:3000
# Default credentials: admin / CHANGE_ME_IN_PRODUCTION
```

### Access Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090
```

### Included Dashboards

- **SceneMachine Overview**: Request rates, latency, memory usage, generation queue, costs

### Alert Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | >5% 5xx errors for 5m | Critical |
| HighLatency | p95 >2s for 5m | Warning |
| PodNotReady | Pod not ready for 5m | Critical |
| HighMemoryUsage | >90% memory for 5m | Warning |
| DatabaseConnectionPoolExhausted | 0 available connections | Critical |
| RedisDown | Redis not responding | Critical |
| GenerationQueueBacklog | >100 jobs for 10m | Warning |

## Backup & Restore

### Automated Backups

- **PostgreSQL**: Daily at 2 AM UTC, retained 7 days
- **Redis**: Daily at 3 AM UTC (BGSAVE trigger)

### Manual Backup

```bash
# PostgreSQL
kubectl exec -n scenemachine postgres-0 -- pg_dump -U scenemachine scenemachine > backup.sql

# Redis
kubectl exec -n scenemachine deploy/redis -- redis-cli BGSAVE
```

### Restore

```bash
# PostgreSQL
kubectl exec -i -n scenemachine postgres-0 -- psql -U scenemachine scenemachine < backup.sql
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend -n scenemachine --replicas=5
```

### HPA Behavior

- Scale up: Aggressive (100% increase or +4 pods every 15s)
- Scale down: Conservative (10% decrease every 60s, 5m stabilization)
- CPU target: 70%
- Memory target: 80%

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n scenemachine
kubectl describe pod <pod-name> -n scenemachine
kubectl logs <pod-name> -n scenemachine
```

### Check Events

```bash
kubectl get events -n scenemachine --sort-by='.lastTimestamp'
```

### Database Connection Issues

```bash
# Test PostgreSQL connectivity
kubectl exec -n scenemachine deploy/backend -- pg_isready -h postgres-service -U scenemachine

# Test Redis connectivity
kubectl exec -n scenemachine deploy/backend -- redis-cli -h redis-service ping
```

### Resource Issues

```bash
# Check resource usage
kubectl top pods -n scenemachine
kubectl top nodes

# Check PVC status
kubectl get pvc -n scenemachine
```

## Security Notes

1. **Secrets**: Never commit real secrets. Use external secret managers (Vault, AWS Secrets Manager) in production.
2. **Network Policy**: Default deny with explicit allow rules for inter-service communication.
3. **Pod Security**: Non-root containers, read-only filesystems where possible.
4. **TLS**: All external traffic via HTTPS (cert-manager + Let's Encrypt).

## Customization

### Custom Domain

Edit `k8s/overlays/production/kustomization.yaml`:

```yaml
patches:
  - patch: |-
      - op: replace
        path: /spec/tls/0/hosts/0
        value: api.yourdomain.com
      - op: replace
        path: /spec/rules/0/host
        value: api.yourdomain.com
    target:
      kind: Ingress
```

### Custom Resource Limits

Edit `k8s/overlays/production/kustomization.yaml` or create additional patches.

### Adding Environment Variables

Add to `configMapGenerator` in the overlay's kustomization.yaml.
