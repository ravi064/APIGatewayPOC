# APIGatewayPOC

> Production-ready API Gateway demonstration using Envoy, Keycloak, and FastAPI microservices

A proof-of-concept microservices application demonstrating API Gateway patterns with OAuth 2.0 authentication, JWT token validation, and role-based access control.

## Quick Start

**Get running in 5 minutes:** See [QUICK_START.md](QUICK_START.md)

**Full documentation:** Browse [docs/](docs/)

## Architecture

```
┌─────────────────────────────────────────────┐
│          API Gateway (Envoy)                │
│     Port 8080 (API) | Port 9901 (Admin)     │
│   + JWT Auth + External Authorization       │
└────┬────────────────┬────────────────┬──────┘
     │                │                │
     │         ┌──────▼──────┐         │
     │         │   AuthZ     │         │
     │         │  Service    │         │
     │         │  Port 9000  │         │
     │         │ (Roles from |         │
     │         |   Database  │         |
     │         └─────────────┘         │
     │                                 │
┌────▼──────┐               ┌──────────▼─────┐
│ Keycloak  │               │ Microservices  │
│ IAM/Auth  │               │Customer/Product|
│Port 8180  │               │Ports 8001/8002 │
└───────────┘               └────────────────┘
```

## Features

- **API Gateway**: Envoy proxy with routing and load balancing
- **Authentication**: Keycloak OAuth 2.0 / OpenID Connect
- **External Authorization**: Separate authz service for role management (PostgreSQL-backed)
- **Security**: JWT token validation, external authz, client secrets, RBAC
- **Microservices**: FastAPI-based customer and product services
- **Containerization**: Docker Compose orchestration
- **Production-Ready**: Security best practices and comprehensive documentation

## Documentation

### Quick Start
- [5-Minute Setup](QUICK_START.md) - Get running quickly
- [Developer Guide](docs/developer-guide.md) - Common commands and testing

### By Role
- **UI Developers**: [UI Developer Guide](docs/ui-developer-guide.md) - React authentication
- **Backend Developers**: [Backend Developer Guide](docs/backend-developer-guide.md) - FastAPI services
- **DevOps/Security**: [Production Deployment](docs/production-deployment-guide.md) - Deployment checklist

### Essential Topics
- **Security**: [Security Quick Start](docs/security/security-quick-start.md) | [Detailed Guide](docs/security/security-guide.md)
- **Architecture**: [System Architecture](docs/architecture/system-architecture.md)
- **API Docs**: [API Documentation](docs/api/README.md) | [Generate Docs](docs/api/API_GENERATION_GUIDE.md)

[Browse all documentation →](docs/README.md)

## Quick Commands

```bash
# Start all services
docker-compose up -d

# Get access token
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=test-client" \
 -d "username=testuser" \
 -d "password=testpass" \
 -d "grant_type=password" | jq -r '.access_token')

# Access protected endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

See [Developer Guide](docs/developer-guide.md) for more commands.

## API Endpoints

### Through API Gateway (Port 8080) - JWT Required

#### Customer Service
- `GET /customers` - List all customers
- `GET /customers/{id}` - Get customer by ID
- `GET /customers/health` - Health check

#### Product Service
- `GET /products` - List all products
- `GET /products/{id}` - Get product by ID
- `GET /products/category/{category}` - Filter by category
- `GET /products/health` - Health check

**Full API Documentation**: [docs/api/README.md](docs/api/README.md)  
**Interactive Docs**: http://localhost:8001/docs (Customer) | http://localhost:8002/docs (Product)

### Authentication
- **Keycloak Admin**: http://localhost:8180 (admin/admin)
- **Token Endpoint**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token

## Security

This project implements enterprise-grade security:
- [x] OAuth 2.0 / OpenID Connect authentication
- [x] JWT token validation at API Gateway
- [x] Client secret authentication
- [x] Role-based access control (RBAC)
- [x] Restricted redirect URIs
- [x] Service-to-service authentication

**Important**: 
- Default secrets are for development only
- See [Security Guide](docs/security/security-guide.md) for production deployment
- Review [Production Checklist](docs/security/security-guide.md#production-security-checklist)

## Project Structure

```
APIGatewayPOC/
├── README.md             # This file
├── QUICK_START.md        # 5-minute getting started guide
├── docker-compose.yml    # Service orchestration
├── .env.example          # Environment variables template
│
├── docs/                 # Documentation
│   ├── README.md         # Documentation index
│   ├── setup/            # Installation and setup guides
│   ├── security/         # Security documentation
│   ├── development/      # Developer guides
│   ├── api/              # Auto-generated API documentation
│   └── architecture/     # Architecture documentation
│   └── test/             # Testing related documentation
│
├── services/             # Microservices
│   ├── gateway/          # Envoy API Gateway
│   ├── keycloak/         # Keycloak IAM
│   ├── authz-service/    # Authorization service (role lookup)
│   ├── customer-service/ # Customer API
│   ├── product-service/  # Product API
│   └── shared/           # Shared utilities
│
├── tests/# All tests
│   ├── test_customer_service.py  # Integration tests for Customer service
│   ├── test_product_service.py   # Integration tests for Product service
│   └── integration/              # Integration test suites
│
└── scripts/  # Utility scripts
    ├── validate_project.py      # Project validation tool
    ├── generate-api-docs.py     # API documentation generator
    ├── rotate-secrets.sh        # Secret rotation (Bash)
    ├── rotate-secrets.ps1       # Secret rotation (PowerShell)
    ├── start.sh                 # Start services
    ├── stop.sh                  # Stop services
    └── test.sh                  # Run tests
```

## Technology Stack

- **API Gateway**: Envoy Proxy v1.28
- **Authentication**: Keycloak 23.0
- **Backend**: FastAPI 0.104.1 (Python 3.12)
- **Containerization**: Docker & Docker Compose
- **Testing**: pytest, requests
- **Data Validation**: Pydantic 2.5.0

## Current Status

This POC demonstrates a production-ready API Gateway with:
- External authorization service with Redis caching
- JWT authentication via Keycloak
- Role-based access control
- React UI integration via `/auth/me` endpoint

## Future Ideas

Potential enhancements for exploration (no commitment):
- Database integration (PostgreSQL) for persistent storage
- Full CRUD operations for services
- Observability stack (distributed tracing, metrics)
- Advanced gateway features (rate limiting, circuit breakers)
- Kubernetes deployment for cloud-native orchestration
- CI/CD pipelines for automated testing and deployment

## Troubleshooting

**Services won't start:**
```bash
docker-compose down
docker-compose up -d --build
```

**Authentication issues:**
- Verify Keycloak is running: `docker-compose logs keycloak`
- Check token hasn't expired (5 min default)
- See [Security Quick Start](docs/security/security-quick-start.md)

**Need more help?**
- Review [Documentation](docs/README.md)

## License

This project is licensed under the MIT License.

---

**Documentation**: [docs/](docs/) | **Quick Start**: [QUICK_START.md](QUICK_START.md) | **Security**: [docs/security/](docs/security/)

