# Quick Reference Guide - APIGatewayPOC

##  Common Commands

### Start Services
```bash
docker-compose up --build          # Build and start all services
docker-compose up -d --build       # Start in background (detached mode)
```

### Stop Services
```bash
docker-compose down                # Stop and remove containers
docker-compose down -v             # Also remove volumes
docker-compose down --rmi all      # Also remove images
```

### View Logs
```bash
docker-compose logs -f                    # All services
docker-compose logs -f gateway            # Gateway only
docker-compose logs -f customer-service   # Customer service only
docker-compose logs -f product-service    # Product service only
```

### Restart Single Service
```bash
docker-compose restart customer-service
docker-compose restart product-service
docker-compose restart gateway
```

### Rebuild Single Service
```bash
docker-compose up -d --build customer-service
docker-compose up -d --build product-service
```

##  Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
pytest tests/test_customer_service.py -v
pytest tests/test_product_service.py -v
pytest tests/integration/test_api_gateway.py -v
pytest tests/integration/test_external_authz.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=services --cov-report=html
```

##  Validation

### Validate Project Structure
```bash
python validate_project.py
```

### Validate Docker Compose
```bash
docker-compose config
```

### Check Python Syntax
```bash
python -m py_compile services/customer-service/main.py
python -m py_compile services/product-service/main.py
```

##  API Endpoints

### Through Gateway (http://localhost:8080)

#### Customer Service
```bash
# Get all customers
curl http://localhost:8080/customers

# Get customer by ID
curl http://localhost:8080/customers/1

# Health check
curl http://localhost:8080/customers/health
```

#### Product Service
```bash
# Get all products
curl http://localhost:8080/products

# Get product by ID
curl http://localhost:8080/products/1

# Get products by category
curl http://localhost:8080/products/category/Electronics

# Health check
curl http://localhost:8080/products/health
```

### Direct Service Access

#### Customer Service (http://localhost:8001)
```bash
curl http://localhost:8001/customers
curl http://localhost:8001/customers/1
curl http://localhost:8001/customers/health
```

#### Product Service (http://localhost:8002)
```bash
curl http://localhost:8002/products
curl http://localhost:8002/products/1
curl http://localhost:8002/products/category/Electronics
curl http://localhost:8002/products/health
```

#### Envoy Admin (http://localhost:9901)
```bash
# Stats
curl http://localhost:9901/stats

# Clusters
curl http://localhost:9901/clusters

# Config dump
curl http://localhost:9901/config_dump

# Server info
curl http://localhost:9901/server_info
```

##  Troubleshooting

### Services Won't Start
```bash
# Check if ports are available
netstat -an | findstr "8080 8001 8002 9901"

# Clean everything and rebuild
docker-compose down -v --rmi all
docker-compose up --build
```

### Check Service Health
```bash
# Through gateway
curl http://localhost:8080/customers/health
curl http://localhost:8080/products/health

# Direct access
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### View Service Logs
```bash
# Last 100 lines
docker-compose logs --tail=100 customer-service

# Follow logs in real-time
docker-compose logs -f customer-service

# All logs
docker-compose logs customer-service
```

### Restart Everything
```bash
docker-compose restart
```

### Check Container Status
```bash
docker-compose ps
docker ps
```

### Access Container Shell
```bash
docker-compose exec customer-service /bin/sh
docker-compose exec product-service /bin/sh
docker-compose exec gateway /bin/sh
```

##  Monitoring

### Check Resource Usage
```bash
docker stats
```

### Check Envoy Stats
```bash
curl http://localhost:9901/stats/prometheus
```

### View Network
```bash
docker network ls
docker network inspect apigatewaypoc_microservices-network
```

##  Development

### Install Dependencies Locally (for IDE support)
```bash
pip install -r services/customer-service/requirements.txt
pip install -r services/product-service/requirements.txt
pip install -r tests/requirements.txt
```

### Run Service Locally (without Docker)
```bash
# Customer Service
cd services/customer-service
uvicorn main:app --reload --port 8001

# Product Service
cd services/product-service
uvicorn main:app --reload --port 8002
```

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
flake8 services/ tests/
```

##  Git Commands

### Check Status
```bash
git status
```

### Commit Changes
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### View Changes
```bash
git diff
git diff HEAD
```

### Create Branch
```bash
git checkout -b feature/your-feature-name
```

##  Port Reference

| Service | Port | Access |
|---------|------|--------|
| API Gateway | 8080 | http://localhost:8080 |
| Envoy Admin | 9901 | http://localhost:9901 |
| Customer Service | 8001 | http://localhost:8001 |
| Product Service | 8002 | http://localhost:8002 |

##  Documentation Files

- **README.md** - Main documentation
- **.copilot-instructions.md** - Development guidelines
- **PROJECT_STATUS.md** - Current project status
- **VERIFICATION_REPORT.md** - Verification details
- **QUICK_REFERENCE.md** - This file

##  Getting Help

### Check Documentation
1. Read README.md
2. Review .copilot-instructions.md
3. Check VERIFICATION_REPORT.md

### Validate Setup
```bash
python validate_project.py
```

### Check Logs
```bash
docker-compose logs -f
```

### Test Endpoints
```bash
curl http://localhost:8080/customers/health
curl http://localhost:8080/products/health
```