# Production Deployment Guide

Essential checklist and steps for deploying the API Gateway to production.

## Pre-Deployment Checklist

### Security
- [ ] Rotate all client secrets
- [ ] Store secrets in vault/secret manager (not in code)
- [ ] Enable SSL/TLS (sslRequired: "external")
- [ ] Configure proper redirect URIs for production domains
- [ ] Disable test-client in Keycloak
- [ ] Review and restrict CORS policies
- [ ] Enable audit logging in Keycloak
- [ ] Configure rate limiting in Envoy

### Infrastructure
- [ ] Set up production database (PostgreSQL)
- [ ] Configure Redis for caching with persistence
- [ ] Set up load balancer for gateway
- [ ] Configure health check endpoints
- [ ] Set up backup and disaster recovery
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerting

### Configuration
- [ ] Update environment variables for production
- [ ] Configure proper JWT token expiration (15-30 min)
- [ ] Set appropriate cache TTL values
- [ ] Configure service timeouts
- [ ] Set proper resource limits (CPU/memory)
- [ ] Configure auto-scaling policies

## Environment Variables

### Required for Production

**Keycloak:**
```bash
KC_BOOTSTRAP_ADMIN_USERNAME=<strong-username>
KC_BOOTSTRAP_ADMIN_PASSWORD=<strong-password>
KC_DB_URL=<postgresql-connection-string>
KC_HOSTNAME=<production-domain>
KC_HTTP_ENABLED=false
KC_HTTPS_ENABLED=true
```

**Authorization Service:**
```bash
SERVICE_PORT=9000
LOG_LEVEL=INFO
REDIS_URL=redis://<redis-host>:6379
REDIS_TTL=300
DATABASE_URL=<postgresql-connection-string>
```

**Gateway:**
```bash
ENVOY_ADMIN_PORT=9901
LOG_LEVEL=info
```

**Services (Customer/Product):**
```bash
SERVICE_NAME=<service-name>
SERVICE_PORT=8000
LOG_LEVEL=INFO
DATABASE_URL=<postgresql-connection-string>
```

## Secret Management

### Generate Secure Secrets

```bash
# Linux/Mac
openssl rand -base64 32

# PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

### Store Secrets Securely

**Option 1: Environment Variables**
```bash
export API_GATEWAY_CLIENT_SECRET=<secret>
export CUSTOMER_SERVICE_SECRET=<secret>
export PRODUCT_SERVICE_SECRET=<secret>
```

**Option 2: Docker Secrets (Swarm)**
```bash
echo "<secret>" | docker secret create gateway_secret -
```

**Option 3: Kubernetes Secrets**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secrets
type: Opaque
data:
  client-secret: <base64-encoded-secret>
```

**Option 4: Vault/Secret Manager**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name api-gateway-secret \
  --secret-string "<secret>"

# HashiCorp Vault
vault kv put secret/api-gateway client_secret=<secret>
```

## SSL/TLS Configuration

### Keycloak

Update realm settings:
```json
{
  "sslRequired": "external",
  "realm": "api-gateway-poc"
}
```

### Envoy (Gateway)

Add TLS configuration to `envoy.yaml`:
```yaml
listeners:
- name: listener_0
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 443
  filter_chains:
  - filters:
    # ... existing filters
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
        common_tls_context:
          tls_certificates:
          - certificate_chain:
              filename: /etc/ssl/certs/server.crt
            private_key:
              filename: /etc/ssl/private/server.key
```

## Database Setup

### PostgreSQL for AuthZ Service

```sql
CREATE DATABASE authz_db;

CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    roles TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_roles_email ON user_roles(email);
```

### Connection Configuration

```python
# services/authz-service/authz_data_access.py
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def get_user_roles(email: str):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT roles FROM user_roles WHERE email = %s", (email,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result[0] if result else []
```

## Redis Configuration

### Production Redis Setup

```yaml
# docker-compose.yml or Kubernetes
redis:
  image: redis:7-alpine
  command: redis-server --requirepass <strong-password> --maxmemory 1gb --maxmemory-policy allkeys-lru
  volumes:
    - redis-data:/data
  restart: always
```

### Enable Persistence

```bash
# Redis config
appendonly yes
appendfilename "appendonly.aof"
save 900 1
save 300 10
save 60 10000
```

## Monitoring

### Health Checks

```yaml
# Kubernetes liveness/readiness probes
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Metrics

**Envoy Admin Interface:**
```bash
curl http://<gateway>:9901/stats/prometheus
```

**Custom Metrics:**
```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

### Logging

**Centralized Logging:**
```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Log Aggregation (ELK/Loki):**
```yaml
# Promtail config for Loki
scrape_configs:
  - job_name: api-gateway
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
```

## Deployment Options

### Docker Compose (Single Host)

```bash
# Production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml api-gateway
```

### Kubernetes

```yaml
# Deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: gateway
        image: api-gateway:latest
        ports:
        - containerPort: 8080
        env:
        - name: LOG_LEVEL
          value: "info"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Backup and Recovery

### Database Backups

```bash
# PostgreSQL backup
pg_dump -U postgres authz_db > backup_$(date +%Y%m%d).sql

# Automated backup
0 2 * * * /usr/bin/pg_dump -U postgres authz_db > /backups/authz_$(date +\%Y\%m\%d).sql
```

### Redis Backups

```bash
# Redis snapshot
redis-cli BGSAVE

# Copy RDB file
cp /var/lib/redis/dump.rdb /backups/redis_$(date +%Y%m%d).rdb
```

### Keycloak Export

```bash
# Export realm
docker exec keycloak /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm api-gateway-poc
```

## Rollback Plan

1. **Keep previous version images**
   ```bash
   docker tag api-gateway:latest api-gateway:v1.0
   ```

2. **Quick rollback command**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.v1.0.yml up -d
   ```

3. **Database rollback**
   ```bash
   psql -U postgres authz_db < backup_YYYYMMDD.sql
   ```

## Performance Tuning

### Gateway (Envoy)

```yaml
# Increase connection pool
circuit_breakers:
  thresholds:
  - priority: DEFAULT
    max_connections: 1024
    max_pending_requests: 1024
    max_requests: 1024
```

### Redis

```bash
# Tune max connections
maxclients 10000

# Tune memory
maxmemory 2gb
```

### FastAPI Services

```python
# Increase workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Post-Deployment Verification

```bash
# Health checks
curl https://<domain>/customers/health
curl https://<domain>/products/health

# Authentication test
TOKEN=$(curl -X POST https://<domain>/auth/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=<client>&client_secret=<secret>&grant_type=client_credentials" \
  | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" https://<domain>/customers

# Load test
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" https://<domain>/customers
```

## Troubleshooting

**Service won't start:**
```bash
docker logs <container-id>
docker-compose logs <service-name>
```

**Database connection issues:**
```bash
# Test connection
psql -h <host> -U <user> -d <database>
```

**SSL certificate issues:**
```bash
# Verify certificate
openssl s_client -connect <domain>:443
```

**Performance issues:**
```bash
# Check resource usage
docker stats
kubectl top pods
```

## Support Contacts

- **Infrastructure:** DevOps team
- **Security:** Security team
- **Database:** DBA team
- **Application:** Development team

## Additional Resources

- [Security Guide](security/security-guide.md) - Detailed security configuration
- [Security Quick Start](security/security-quick-start.md) - Security essentials
- [Backend Developer Guide](BACKEND_DEVELOPER_GUIDE.md) - Service development
- [UI Developer Guide](UI_DEVELOPER_GUIDE.md) - Frontend integration

---

**Remember:** Test all changes in staging before deploying to production.
