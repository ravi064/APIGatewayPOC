# Backend Developer Guide

Quick reference for FastAPI backend developers working with the API Gateway.

## Architecture Overview

```
Gateway (Envoy) → External AuthZ → Your Service
       ↓              ↓                ↓
   JWT Valid    Adds Headers    Receives Headers
                x-user-email
                x-user-roles
```

**Your service receives:**
- `x-user-email`: Authenticated user's email
- `x-user-roles`: Comma-separated roles (e.g., "user,customer-manager")

## Quick Start

### 1. Create New Service

```python
from fastapi import FastAPI, Request, HTTPException
import sys
sys.path.append('/app')

from shared.common import setup_logging, create_health_response

# Setup logging
logger = setup_logging("my-service")

app = FastAPI(
    title="My Service",
    description="Service description",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return create_health_response("my-service")

@app.get("/my-endpoint")
def my_endpoint(request: Request):
    # Get user info from headers (added by authz service)
    email = request.headers.get("x-user-email", "")
    roles = request.headers.get("x-user-roles", "").split(",")
    
    logger.info(f"Request from {email} with roles {roles}")
    
    return {"message": "Hello", "user": email}
```

### 2. Add to docker-compose.yml

```yaml
my-service:
  build:
    context: ./services
    dockerfile: my-service/Dockerfile
  ports:
    - "8003:8000"
  environment:
    - SERVICE_NAME=my-service
    - SERVICE_PORT=8000
  networks:
    - microservices-network
```

### 3. Create Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY shared/ /app/shared/
COPY my-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY my-service/ .
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8000}"]
```

### 4. Register in Envoy

Add to `services/gateway/envoy.yaml`:

```yaml
# In routes section:
- match:
    prefix: "/my-resource"
  route:
    cluster: my_service

# In clusters section:
- name: my_service
  connect_timeout: 30s
  type: LOGICAL_DNS
  dns_lookup_family: V4_ONLY
  lb_policy: ROUND_ROBIN
  load_assignment:
    cluster_name: my_service
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: my-service
              port_value: 8000
```

## Authorization Patterns

### Pattern 1: Role-Based Access

```python
from fastapi import HTTPException

def require_roles(request: Request, required_roles: list):
    roles = request.headers.get("x-user-roles", "").split(",")
    
    if not any(role in roles for role in required_roles):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

@app.get("/admin/users")
def admin_endpoint(request: Request):
    require_roles(request, ["admin", "customer-manager"])
    return {"users": [...]}
```

### Pattern 2: User-Scoped Data

```python
@app.get("/my-data")
def get_my_data(request: Request):
    email = request.headers.get("x-user-email")
    
    # Filter data by authenticated user
    data = db.query(Model).filter(Model.email == email).all()
    return data
```

### Pattern 3: Hierarchical Permissions

```python
def check_permission(request: Request, resource_id: int):
    email = request.headers.get("x-user-email")
    roles = request.headers.get("x-user-roles", "").split(",")
    
    # Admins can access everything
    if "admin" in roles:
        return True
    
    # Managers can access their department
    if "manager" in roles:
        resource = db.get(resource_id)
        return resource.department == user.department
    
    # Regular users can only access their own
    resource = db.get(resource_id)
    return resource.owner_email == email
```

## Shared Utilities

### Logging

```python
from shared.common import setup_logging

logger = setup_logging("my-service")

logger.info("Info message")
logger.error("Error message", exc_info=True)
logger.warning("Warning message")
```

### Health Check

```python
from shared.common import create_health_response

@app.get("/health")
def health_check():
    response = create_health_response("my-service")
    # Add custom health checks
    response["database_healthy"] = check_database()
    return response
```

### Authentication Headers

```python
from shared.auth import get_user_email, get_user_roles

@app.get("/endpoint")
def my_endpoint(request: Request):
    email = get_user_email(request)
    roles = get_user_roles(request)
    
    logger.info(f"User {email} with roles {roles}")
    return {"user": email, "roles": roles}
```

## Testing

### Unit Tests

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_endpoint_with_roles():
    headers = {
        "x-user-email": "test@example.com",
        "x-user-roles": "user,admin"
    }
    
    response = client.get("/endpoint", headers=headers)
    assert response.status_code == 200
```

### Integration Tests

```python
import requests

def test_via_gateway():
    # Get token
    token_response = requests.post(
        "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token",
        data={
            "client_id": "test-client",
            "username": "testuser",
            "password": "testpass",
            "grant_type": "password"
        }
    )
    token = token_response.json()["access_token"]
    
    # Call service through gateway
    response = requests.get(
        "http://localhost:8080/my-resource",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

## Best Practices

### 1. Always Use Shared Utilities

```python
# Good
from shared.common import setup_logging
logger = setup_logging("my-service")

# Bad
import logging
logger = logging.getLogger(__name__)
```

### 2. Trust Gateway Headers

Gateway validates JWT before your service sees the request. Headers are trustworthy within the internal network.

### 3. Validate Business Logic Only

```python
# Gateway already checked authentication
# You only validate business rules

@app.put("/customers/{id}")
def update_customer(id: int, request: Request):
    roles = request.headers.get("x-user-roles", "").split(",")
    
    # Business logic validation
    if "customer-manager" not in roles:
        raise HTTPException(403, "Need customer-manager role")
    
    # Update customer
    ...
```

### 4. Log User Context

```python
logger.info(f"[{email}] Processing request for resource {id}")
```

### 5. Return Consistent Errors

```python
from fastapi import HTTPException

# Use standard HTTP status codes
raise HTTPException(status_code=403, detail="Insufficient permissions")
raise HTTPException(status_code=404, detail="Resource not found")
raise HTTPException(status_code=400, detail="Invalid request")
```

## Common Patterns

### Pydantic Models

```python
from pydantic import BaseModel

class CustomerRequest(BaseModel):
    name: str
    email: str

class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    owner_email: str

@app.post("/customers", response_model=CustomerResponse)
def create_customer(customer: CustomerRequest, request: Request):
    owner_email = request.headers.get("x-user-email")
    # Create customer with owner
    ...
```

### Database Access

```python
# Simple mock pattern (current)
CUSTOMERS_DB = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}

@app.get("/customers/{id}")
def get_customer(id: int):
    if id not in CUSTOMERS_DB:
        raise HTTPException(404, "Customer not found")
    return CUSTOMERS_DB[id]
```

### Error Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

## Environment Variables

```python
import os

SERVICE_NAME = os.getenv("SERVICE_NAME", "my-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

## Project Structure

```
services/
  my-service/
    main.py              # FastAPI app
    requirements.txt     # Python dependencies
    Dockerfile           # Container definition
    models/              # Pydantic models (optional)
      __init__.py
      customer.py
    my_service_data_access.py  # Data layer (optional)
```

## Dependencies

### requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
requests==2.31.0
```

## Debugging

### View Logs

```bash
docker-compose logs -f my-service
```

### Test Directly

```bash
# Bypass gateway (for debugging)
curl -H "x-user-email: test@example.com" \
     -H "x-user-roles: user,admin" \
     http://localhost:8003/endpoint
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Shared Utilities](../services/shared/) - Common functions
- [Customer Service](../services/customer-service/) - Reference implementation
- [Product Service](../services/product-service/) - Reference implementation
- [Security Guide](security/security-guide.md) - Authentication details

## Quick Reference

```python
# Basic endpoint
@app.get("/resource")
def get_resource(request: Request):
    email = request.headers.get("x-user-email")
    roles = request.headers.get("x-user-roles", "").split(",")
    return {"data": [...]}

# Protected endpoint
@app.post("/admin/resource")
def admin_resource(request: Request):
    roles = request.headers.get("x-user-roles", "").split(",")
    if "admin" not in roles:
        raise HTTPException(403, "Admin only")
    return {"created": True}

# Health check
@app.get("/health")
def health():
    return create_health_response("my-service")
```

---

**Need examples?** Check [Customer Service](../services/customer-service/main.py) for a complete reference implementation.
