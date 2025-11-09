# Developer Guide

Common commands, testing, and troubleshooting for the API Gateway POC.

## Quick Start

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Common Commands

### Service Management

```bash
# Start with rebuild
docker-compose up --build -d

# Restart specific service
docker-compose restart customer-service

# View service status
docker-compose ps

# Access container shell
docker-compose exec customer-service /bin/sh
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gateway
docker-compose logs -f authz-service
docker-compose logs -f keycloak

# Last 100 lines
docker-compose logs --tail=100 customer-service

# PowerShell: Filter logs
docker-compose logs authz-service | Select-String "Cache HIT"
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Also remove volumes
docker-compose down -v

# Remove everything including images
docker-compose down -v --rmi all
```

## Authentication

### Get JWT Token

**Bash:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password" | jq -r '.access_token')
```

**PowerShell:**
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token" `
  -Method POST -ContentType "application/x-www-form-urlencoded" `
  -Body @{client_id="test-client"; username="testuser"; password="testpass"; grant_type="password"}
$TOKEN = $response.access_token
```

### Use Token

**Bash:**
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/customers" -Headers @{Authorization="Bearer $TOKEN"}
```

## Testing

### Run All Tests

```bash
# Activate virtual environment (if needed)
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services --cov-report=html
```

### Run Specific Tests

```bash
# Customer service tests
pytest tests/test_customer_service.py -v

# Product service tests
pytest tests/test_product_service.py -v

# Integration tests
pytest tests/integration/ -v

# External authz tests
pytest tests/integration/test_external_authz.py -v

# Single test
pytest tests/test_customer_service.py::test_get_all_customers -v
```

### Manual API Testing

```bash
# Health checks
curl http://localhost:8080/customers/health
curl http://localhost:8080/products/health

# Get all customers (requires JWT)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers

# Get specific customer
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers/1

# Get all products (no JWT required)
curl http://localhost:8080/products

# Get products by category
curl http://localhost:8080/products/category/Electronics
```

## API Endpoints

### Through Gateway (Port 8080)

**Customer Service (JWT Required):**
```
GET /customers          - List customers
GET /customers/{id}     - Get customer by ID
GET /customers/health   - Health check
```

**Product Service:**
```
GET /products                    - List products
GET /products/{id}               - Get product by ID
GET /products/category/{cat}     - Filter by category
GET /products/health             - Health check
```

**Auth Endpoints:**
```
GET  /auth/me                    - Get current user (JWT required)
POST /auth/realms/.../token      - Get token from Keycloak
```

### Direct Service Access

```
http://localhost:8001  - Customer service
http://localhost:8002  - Product service
http://localhost:9000  - AuthZ service (internal)
http://localhost:8180  - Keycloak admin
http://localhost:9901  - Envoy admin
```

## Monitoring

### Service Health

```bash
# Through gateway
curl http://localhost:8080/customers/health
curl http://localhost:8080/products/health

# Direct access
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Envoy Admin

```bash
# Stats
curl http://localhost:9901/stats

# Clusters
curl http://localhost:9901/clusters

# Config dump
curl http://localhost:9901/config_dump

# Prometheus metrics
curl http://localhost:9901/stats/prometheus
```

### Resource Usage

```bash
# Container stats
docker stats

# Specific service
docker stats customer-service

# Check disk usage
docker system df
```

## Troubleshooting

### Services Won't Start

```bash
# Check if ports are in use
netstat -an | findstr "8080 8001 8002 9901"  # Windows
netstat -tuln | grep "8080\|8001\|8002\|9901"  # Linux

# Clean and rebuild
docker-compose down -v
docker-compose up --build
```

### Authentication Issues

```bash
# Check Keycloak is running
docker-compose ps keycloak
docker-compose logs keycloak

# Test token endpoint directly
curl http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token

# Check token expiration (tokens expire in 5 min)
# Get a new token if expired
```

### Service Can't Connect

```bash
# Check network
docker network ls
docker network inspect apigatewaypoc_microservices-network

# Test service-to-service connectivity
docker-compose exec gateway ping authz-service
docker-compose exec gateway curl http://authz-service:9000/authz/health
```

### 401/403 Errors

```bash
# 401: Authentication failed
# - Check token is valid and not expired
# - Verify Authorization header format: "Bearer <token>"

# 403: Authorization failed
# - User authenticated but lacks required role
# - Check user roles: curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/auth/me
```

### Gateway Issues

```bash
# Check Envoy config
docker-compose exec gateway cat /etc/envoy/envoy.yaml

# Validate config
docker-compose config

# Check gateway logs
docker-compose logs gateway | grep -i error
```

## Development Workflow

### Adding a New Endpoint

1. Update FastAPI service (`main.py`)
2. Add tests (`tests/test_<service>.py`)
3. Run tests locally
4. Rebuild and test: `docker-compose up --build -d`
5. Generate API docs: `python scripts/generate-api-docs.py`

### Making Code Changes

1. Edit code in `services/<service>/`
2. Rebuild specific service: `docker-compose up --build -d <service>`
3. View logs: `docker-compose logs -f <service>`
4. Test changes
5. Run full test suite

### Adding a New Service

1. Create service directory: `services/my-service/`
2. Add `main.py`, `Dockerfile`, `requirements.txt`
3. Add to `docker-compose.yml`
4. Register in `services/gateway/envoy.yaml`
5. Add tests
6. Update documentation

## API Documentation

### Generate API Docs

```bash
# Ensure services are running
docker-compose up -d

# Generate markdown docs
python scripts/generate-api-docs.py

# View docs
cat docs/api/README.md
```

### Interactive API Docs

Visit in browser:
- Customer: http://localhost:8001/docs
- Product: http://localhost:8002/docs

## Code Quality

### Format Code

```bash
# Install black
pip install black

# Format all Python files
black services/ tests/
```

### Lint Code

```bash
# Install flake8
pip install flake8

# Lint all Python files
flake8 services/ tests/ --max-line-length=120
```

### Type Checking

```bash
# Install mypy
pip install mypy

# Type check
mypy services/ --ignore-missing-imports
```

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Gateway | 8080 | http://localhost:8080 |
| Envoy Admin | 9901 | http://localhost:9901 |
| Customer Service | 8001 | http://localhost:8001 |
| Product Service | 8002 | http://localhost:8002 |
| AuthZ Service | 9000 | Internal only |
| Keycloak | 8180 | http://localhost:8180 |
| Redis | 6379 | Internal only |

## Environment Variables

### Development (Default)

```bash
SERVICE_NAME=customer-service
SERVICE_PORT=8000
LOG_LEVEL=INFO
REDIS_URL=redis://redis:6379
REDIS_TTL=300
```

### Override for Testing

```bash
# Create .env file
echo "LOG_LEVEL=DEBUG" > .env
echo "REDIS_TTL=60" >> .env

# Restart services
docker-compose down
docker-compose up -d
```

## Git Workflow

```bash
# Check status
git status

# Create feature branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push branch
git push origin feature/my-feature
```

## Additional Resources

- [UI Developer Guide](UI_DEVELOPER_GUIDE.md) - React integration
- [Backend Developer Guide](BACKEND_DEVELOPER_GUIDE.md) - FastAPI services
- [Production Deployment](PRODUCTION_DEPLOYMENT.md) - Deployment checklist
- [Security Quick Start](security/security-quick-start.md) - Security essentials
- [API Documentation](api/README.md) - API reference

## Quick Command Reference

```bash
# Start
docker-compose up -d

# Get token
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client&username=testuser&password=testpass&grant_type=password" | jq -r '.access_token')

# Test API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers

# Run tests
pytest tests/ -v

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

**Need more help?** Check the specific guides for [UI](UI_DEVELOPER_GUIDE.md), [Backend](BACKEND_DEVELOPER_GUIDE.md), or [Production](PRODUCTION_DEPLOYMENT.md) development.
