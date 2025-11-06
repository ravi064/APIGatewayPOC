# External Authorization Service Implementation Plan

## Overview

This document outlines the implementation plan for adding an external authorization service to replace Keycloak-based role management. This change aligns with production requirements where roles will be managed in PostgreSQL rather than Keycloak.

**Date Created**: November 5, 2025  
**Status**: Phase A - In Progress

## Business Context

### Current State
- User roles are stored in Keycloak's `realm_access.roles` claim
- Envoy extracts roles from JWT and uses RBAC filter for authorization
- Works well for POC but doesn't match production IT policies

### Target State
- User roles stored in PostgreSQL database
- External authorization service provides role lookup
- Envoy calls authz service for each authenticated request
- Roles cached in Redis for performance
- Keycloak only handles authentication (JWT issuance/validation)

### Why This Change?
- **IT Policy Compliance**: Production environment doesn't allow role management in Keycloak
- **Separation of Concerns**: Authentication (Keycloak) vs Authorization (PostgreSQL)
- **Flexibility**: Easier to integrate with existing enterprise identity systems
- **Performance**: Redis caching ensures low latency

---

## Architecture

### High-Level Flow

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│ Client  │────▶│    Envoy     │────▶│    AuthZ     │────▶│   Redis    │
└─────────┘     │   Gateway    │     │   Service    │     │   Cache    │
                │              │     │              │     └────────────┘
                │ 1. Validate  │     │              │            │
                │    JWT       │     │ 1. Extract   │            │
                │              │     │    email     │     ┌──────▼──────┐
                │ 2. Call      │     │ 2. Check     │────▶│ PostgreSQL  │
                │    /authz/   │     │    cache     │     │   (Mock)    │
                │    roles     │     │ 3. Query DB  │     └─────────────┘
                │              │     │    if miss   │
                │ 3. Receive   │◀────│ 4. Return    │
                │    X-User-   │     │    roles     │
                │    Roles     │     │              │
                │              │     └──────────────┘
                │ 4. RBAC      │
                │    check     │
                │              │
                │ 5. Route to  │
                │    service   │
                └──────┬───────┘
                       │
               ┌───────┴────────┐
               │                │
        ┌──────▼─────┐   ┌─────▼────────┐
        │  Customer  │   │   Product     │
        │  Service   │   │   Service     │
        │ (unchanged)│   │  (unchanged)  │
        └────────────┘   └───────────────┘
```

### Request Flow Details

1. **Client** sends request with JWT Bearer token
2. **Envoy JWT Filter** validates token signature and expiration
3. **Envoy ext_authz Filter** calls AuthZ service at `/authz/roles`
4. **AuthZ Service**:
   - Extracts user email from JWT
   - Checks Redis cache for roles (Phase B only)
   - On cache miss, queries PostgreSQL mock
   - Returns roles in `X-User-Roles` header
5. **Envoy RBAC Filter** checks if roles in `X-User-Roles` header match required roles
6. **Envoy Router** forwards request to appropriate service
7. **Downstream Services** receive request with user context (unchanged)

---

## Implementation Phases

### Phase A: External AuthZ Service (No Redis)

**Goal**: Replace Keycloak roles with external authorization service using mock PostgreSQL data access.

**Duration**: 2-3 hours

**Components**:
- New AuthZ microservice (FastAPI)
- Mock PostgreSQL data access layer
- Updated Envoy configuration (ext_authz filter)
- Updated Envoy RBAC to use header-based roles
- Integration tests

**What's NOT included in Phase A**:
- Redis caching (added in Phase B)
- Real PostgreSQL connection
- Cache invalidation logic

---

### Phase B: Add Redis Caching

**Goal**: Add Redis caching layer to improve performance and reduce database queries.

**Duration**: 1-2 hours

**Components**:
- Redis container in docker-compose
- Redis cache module in AuthZ service
- Cache hit/miss logging
- Cache invalidation endpoint (for testing)
- Performance comparison tests

**Cache Strategy**:
- **Key Format**: `user:roles:{email}`
- **Value Format**: JSON array `["user", "customer-manager"]`
- **TTL**: 300 seconds (5 minutes)
- **Eviction Policy**: allkeys-lru (Least Recently Used)

---

## Technical Specifications

### AuthZ Service API

#### Endpoint 1: Health Check
```http
GET /authz/health

Response: 200 OK
{
  "status": "healthy",
  "service": "authz-service",
  "version": "1.0.0"
}
```

**Purpose**: Health check and liveness probe  
**Access**: Internal Docker network only

---

#### Endpoint 2: Role Lookup
```http
POST /authz/roles

Request Headers:
  Authorization: Bearer <jwt-token>
  X-Request-Id: <uuid>

Response: 200 OK (User found)
Headers:
  X-User-Email: testuser@example.com
  X-User-Roles: user,customer-manager
Body: {}

Response: 403 Forbidden (User not found)
{
  "detail": "User not found in role database"
}

Response: 401 Unauthorized (Invalid JWT)
{
  "detail": "Invalid or missing authorization token"
}

Response: 500 Internal Server Error (Service error)
{
  "detail": "Internal authorization error"
}
```

**Purpose**: Primary role lookup endpoint called by Envoy  
**Access**: Only called by Envoy via internal network  
**Processing**:
1. Extract JWT from Authorization header
2. Decode JWT payload to get user email (no signature verification needed - Envoy already validated)
3. Lookup roles from data source (Phase A: mock DB, Phase B: Redis → PostgreSQL)
4. Return roles in response headers

---

### Mock Database Schema

```python
# Simulates PostgreSQL table: user_roles
# Schema: (email VARCHAR PRIMARY KEY, roles TEXT[])

USER_ROLES_DB = {
    "test.user-unvrfd@example.com": ["unverified-user"],
    "test.user-vrfd@example.com": ["verified-user"],
    "test.user@example.com": ["user"],
    "test.user-cm@example.com": ["user", "customer-manager"],
    "test.user-pm@example.com": ["user", "product-manager"],
    "test.user-pcm@example.com": ["user", "product-category-manager"],
    "admin.user@example.com": ["user", "admin"]
}
```

**Notes**:
- Email is case-insensitive (stored lowercase)
- Roles are comma-separated in response header
- Users not in database will receive 403 Forbidden
- In production, this would be a real PostgreSQL query

---

### Envoy Configuration Changes

#### 1. Add ext_authz Filter (After JWT, Before RBAC)

```yaml
http_filters:
  # 1. JWT Authentication Filter (UNCHANGED)
  - name: envoy.filters.http.jwt_authn
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
      # ... existing JWT config ...
  
  # 2. External Authorization Filter (NEW)
  - name: envoy.filters.http.ext_authz
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
      http_service:
        server_uri:
          uri: http://authz-service:9000
          cluster: authz_service_cluster
          timeout: 1s  # Fast timeout for low latency
        path_prefix: /authz/roles
        authorization_request:
          allowed_headers:
            patterns:
            - exact: authorization      # Forward JWT to authz service
            - exact: x-request-id       # Forward request ID for logging
        authorization_response:
          allowed_upstream_headers:
            patterns:
            - exact: x-user-email       # Add user email to request
            - exact: x-user-roles       # Add user roles to request
      failure_mode_allow: false         # Fail closed if authz service unavailable
  
  # 3. RBAC Filter (MODIFIED - use header-based roles)
  - name: envoy.filters.http.rbac
    # ... see detailed changes below ...
  
  # 4. Router filter (UNCHANGED)
  - name: envoy.filters.http.router
```

#### 2. Modify RBAC Filter to Use Headers

**Before (JWT metadata-based)**:
```yaml
principals:
  - metadata:
      filter: envoy.filters.http.jwt_authn
      path:
      - key: verified_jwt
      - key: realm_access
      - key: roles
      value:
        list_match:
          one_of:
            string_match:
              exact: "user"
```

**After (Header-based)**:
```yaml
principals:
  - header:
      name: "x-user-roles"
      string_match:
        contains: "user"  # Check if "user" is in comma-separated list
```

#### 3. Add AuthZ Service Cluster

```yaml
clusters:
  # ... existing clusters ...
  
  # NEW: Authorization service cluster
  - name: authz_service_cluster
    connect_timeout: 1s
    type: LOGICAL_DNS
    dns_lookup_family: V4_ONLY
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: authz_service_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: authz-service
                port_value: 9000
    health_checks:
    - timeout: 1s
      interval: 10s
      unhealthy_threshold: 2
      healthy_threshold: 2
      http_health_check:
        path: /authz/health
```

---

### Docker Compose Changes

#### Phase A: Add AuthZ Service

```yaml
services:
  # ... existing services ...
  
  # NEW: Authorization Service
  authz-service:
    build:
      context: ./services/authz-service
      dockerfile: Dockerfile
    container_name: authz-service
    environment:
      - SERVICE_PORT=9000
      - LOG_LEVEL=INFO
      - SERVICE_NAME=authz-service
    networks:
      - microservices-network
    # NO ports exposed - internal network only for security
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/authz/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      - keycloak  # Need JWT validation to be working
  
  # Update gateway dependencies
  gateway:
    depends_on:
      - keycloak
      - authz-service  # NEW dependency
      - customer-service
      - product-service
```

#### Phase B: Add Redis

```yaml
services:
  # ... existing services ...
  
  # NEW: Redis Cache
  redis:
    image: redis:7-alpine
    container_name: authz-redis
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    networks:
      - microservices-network
    # Optional: expose for inspection during development
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    volumes:
      - redis-data:/data
  
  # Update authz-service for Redis
  authz-service:
    environment:
      - SERVICE_PORT=9000
      - LOG_LEVEL=INFO
      - SERVICE_NAME=authz-service
      - REDIS_URL=redis://redis:6379  # NEW
      - REDIS_TTL=300                   # NEW: 5 minutes
    depends_on:
      - keycloak
      - redis  # NEW dependency

volumes:
  redis-data:  # NEW: Redis data persistence
```

---

## File Structure

### Phase A Files

```
services/authz-service/
├── main.py                    # FastAPI application
├── authz_data_access.py       # Mock PostgreSQL data access
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
└── README.md                  # Service documentation

tests/
├── test_authz_service.py      # Unit tests for authz service
└── integration/
    └── test_external_authz.py # Integration tests

docs/development/
└── external-authz-implementation-plan.md  # This document
```

### Phase B Additional Files

```
services/authz-service/
├── redis_cache.py             # Redis caching layer
└── (updated) main.py          # Integrate caching
└── (updated) requirements.txt # Add redis package
```

---

## Code Specifications

### main.py Structure

```python
"""
External Authorization Service
Provides role lookup for authenticated users based on email from JWT.
"""

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
import logging
import os
import json
import base64

from authz_data_access import get_user_roles, UserNotFoundException

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Authorization Service",
    description="External authorization service for role lookup",
    version="1.0.0"
)

def extract_email_from_jwt(token: str) -> str:
    """
    Extract email from JWT payload.
    Note: Signature already validated by Envoy, we only decode payload.
    """
    # Implementation details...
    pass

@app.get("/authz/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "authz-service",
        "version": "1.0.0"
    }

@app.post("/authz/roles")
async def get_user_roles_endpoint(request: Request):
    """
    Role lookup endpoint called by Envoy.
    Extracts user email from JWT and returns roles in response headers.
    """
    # Implementation details in Phase A...
    pass
```

### authz_data_access.py Structure

```python
"""
Mock data access layer simulating PostgreSQL role queries.
In production, this would connect to actual PostgreSQL database.
"""

from typing import List
import logging

logger = logging.getLogger(__name__)

# Mock database: user email -> roles mapping
USER_ROLES_DB = {
    "test.user-unvrfd@example.com": ["unverified-user"],
    "test.user-vrfd@example.com": ["verified-user"],
    "test.user@example.com": ["user"],
    "test.user-cm@example.com": ["user", "customer-manager"],
    "test.user-pm@example.com": ["user", "product-manager"],
    "test.user-pcm@example.com": ["user", "product-category-manager"],
    "admin.user@example.com": ["user", "admin"]
}

class UserNotFoundException(Exception):
    """Raised when user email not found in role database"""
    pass

def get_user_roles(email: str) -> List[str]:
    """
    Get roles for a user by email.
    
    Simulates: SELECT roles FROM user_roles WHERE email = ?
    
    Args:
        email: User email address (case-insensitive)
    
    Returns:
        List of role names
    
    Raises:
        UserNotFoundException: If user not found in database
    """
    email_lower = email.lower()
    roles = USER_ROLES_DB.get(email_lower)
    
    if roles is None:
        logger.warning(f"User not found in role database: {email}")
        raise UserNotFoundException(f"No roles found for user: {email}")
    
    logger.info(f"Retrieved roles for {email}: {roles}")
    return roles

def get_all_users() -> dict:
    """Get all users (for debugging/testing only)"""
    return USER_ROLES_DB.copy()
```

### Phase B: redis_cache.py Structure

```python
"""
Redis caching layer for user roles.
Reduces database queries and improves performance.
"""

import redis
import json
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class RolesCache:
    """Redis-based cache for user roles"""
    
    def __init__(self, redis_url: str, ttl: int = 300):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl
        logger.info(f"Redis cache initialized with TTL={ttl}s")
    
    def _make_key(self, email: str) -> str:
        """Generate cache key for user email"""
        return f"user:roles:{email.lower()}"
    
    def get(self, email: str) -> Optional[List[str]]:
        """
        Get roles from cache.
        
        Returns:
            List of roles if found, None if cache miss
        """
        key = self._make_key(email)
        try:
            cached = self.redis_client.get(key)
            if cached:
                roles = json.loads(cached)
                logger.info(f"Cache HIT for {email}")
                return roles
            else:
                logger.info(f"Cache MISS for {email}")
                return None
        except Exception as e:
            logger.error(f"Redis error on get: {e}")
            return None  # Fail gracefully
    
    def set(self, email: str, roles: List[str]) -> bool:
        """
        Set roles in cache with TTL.
        
        Returns:
            True if successful, False otherwise
        """
        key = self._make_key(email)
        try:
            value = json.dumps(roles)
            self.redis_client.setex(key, self.ttl, value)
            logger.info(f"Cached roles for {email} with TTL={self.ttl}s")
            return True
        except Exception as e:
            logger.error(f"Redis error on set: {e}")
            return False  # Fail gracefully
    
    def invalidate(self, email: str) -> bool:
        """
        Invalidate cache for user (useful for testing).
        
        Returns:
            True if key existed and was deleted, False otherwise
        """
        key = self._make_key(email)
        try:
            deleted = self.redis_client.delete(key)
            if deleted:
                logger.info(f"Invalidated cache for {email}")
                return True
            else:
                logger.info(f"No cache entry to invalidate for {email}")
                return False
        except Exception as e:
            logger.error(f"Redis error on invalidate: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if Redis is accessible"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_authz_service.py

def test_get_user_roles_known_user():
    """Test role lookup for known user"""
    roles = get_user_roles("testuser@example.com")
    assert roles == ["user"]

def test_get_user_roles_case_insensitive():
    """Test that email lookup is case-insensitive"""
    roles = get_user_roles("TestUser@Example.COM")
    assert roles == ["user"]

def test_get_user_roles_unknown_user():
    """Test that unknown users raise exception"""
    with pytest.raises(UserNotFoundException):
        get_user_roles("unknown@example.com")

def test_extract_email_from_jwt():
    """Test JWT email extraction"""
    token = create_test_jwt({"email": "test@example.com"})
    email = extract_email_from_jwt(token)
    assert email == "test@example.com"
```

### Integration Tests

```python
# tests/integration/test_external_authz.py

def test_customer_access_with_authz_service():
    """Test full flow: JWT → Envoy → AuthZ → Customer Service"""
    
    # Get token from Keycloak
    token = get_keycloak_token("testuser", "testpass")
    
    # Make request through gateway
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser has 'user' role from authz service)
    assert response.status_code == 200
    
    # Check that roles came from authz service (check logs)
    authz_logs = get_container_logs("authz-service")
    assert "Retrieved roles for testuser@example.com" in authz_logs

def test_customer_manager_access():
    """Test that customer-manager role allows access to all customers"""
    
    token = get_keycloak_token("testuser-cm", "testpass")
    
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    # Should return all customers (testuser-cm has customer-manager role)

def test_unknown_user_blocked():
    """Test that users not in authz database are blocked"""
    
    # Create valid JWT for user not in authz database
    token = create_valid_jwt_for_unknown_user()
    
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should be forbidden (403) because user not in authz database
    assert response.status_code == 403

def test_authz_service_failure_blocks_requests():
    """Test that requests are blocked when authz service is down"""
    
    # Stop authz service
    subprocess.run(["docker-compose", "stop", "authz-service"])
    
    token = get_keycloak_token("testuser", "testpass")
    
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should fail (403 or 503) due to failure_mode_allow: false
    assert response.status_code in [403, 503]
    
    # Restart service
    subprocess.run(["docker-compose", "start", "authz-service"])
```

### Phase B: Cache Tests

```python
def test_cache_hit_reduces_db_queries():
    """Test that second request uses cache"""
    
    token = get_keycloak_token("testuser", "testpass")
    
    # First request - should query database
    response1 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 200
    
    # Check logs for cache miss
    logs1 = get_container_logs("authz-service")
    assert "Cache MISS" in logs1
    
    # Second request - should use cache
    response2 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 200
    
    # Check logs for cache hit
    logs2 = get_container_logs("authz-service", since=logs1[-1]["timestamp"])
    assert "Cache HIT" in logs2

def test_cache_expiration():
    """Test that cache expires after TTL"""
    
    token = get_keycloak_token("testuser", "testpass")
    
    # First request
    requests.get("http://localhost:8080/customers", headers={"Authorization": f"Bearer {token}"})
    
    # Wait for TTL to expire (5+ minutes)
    time.sleep(301)
    
    # Second request - should query database again
    requests.get("http://localhost:8080/customers", headers={"Authorization": f"Bearer {token}"})
    
    # Check logs for cache miss after expiration
    logs = get_container_logs("authz-service")
    assert logs.count("Cache MISS") == 2
```

---

## Security Considerations

### 1. Network Isolation
- ✅ AuthZ service NOT exposed to host (no port mapping)
- ✅ Only accessible via internal Docker network
- ✅ Envoy connects using internal DNS (`authz-service:9000`)

### 2. Authentication
- ✅ JWT validation still performed by Envoy
- ✅ AuthZ service only decodes payload (doesn't validate signature)
- ✅ Invalid/missing JWT rejected before reaching authz service

### 3. Fail-Safe Behavior
- ✅ `failure_mode_allow: false` - requests denied if authz service unavailable
- ✅ Health checks monitor authz service availability
- ✅ Gateway won't start if authz service dependency not ready

### 4. No Test Endpoints
- ✅ No debug/test endpoints in production code
- ✅ Troubleshooting via comprehensive logging
- ✅ Integration tests verify behavior

### 5. Logging & Audit
- ✅ All role lookups logged with request ID
- ✅ User email included in logs for audit trail
- ✅ Cache hit/miss logged for performance monitoring
- ✅ Failed authorization attempts logged

---

## Migration Path

### Step 1: Deploy Phase A
1. Create authz-service
2. Update Envoy configuration
3. Deploy all changes together
4. Run integration tests
5. Monitor logs for issues

### Step 2: Verify Behavior
1. Confirm all existing tests pass
2. Verify roles come from authz service (not Keycloak)
3. Check authz service logs for successful lookups
4. Test with unknown users (should be blocked)

### Step 3: Deploy Phase B (Later)
1. Add Redis container
2. Update authz-service with caching
3. Deploy changes
4. Monitor cache hit/miss rates
5. Verify performance improvement

### Step 4: Production Readiness (Future)
1. Replace mock database with real PostgreSQL
2. Add connection pooling
3. Implement proper cache invalidation
4. Add metrics and monitoring
5. Load testing and performance tuning

---

## Rollback Plan

If issues arise after deployment:

### Quick Rollback (< 5 minutes)
```bash
# Revert to previous commit
git revert HEAD
docker-compose down
docker-compose up -d --build

# OR use previous container images
docker-compose down
docker-compose up -d gateway customer-service product-service
```

### Partial Rollback (Disable External AuthZ)
1. Remove ext_authz filter from envoy.yaml
2. Revert RBAC filter to use JWT metadata
3. Restart gateway only
4. Keep authz-service running for investigation

---

## Performance Expectations

### Phase A (No Cache)
- **Latency per request**: +5-15ms (authz service call + mock DB lookup)
- **Throughput**: Limited by authz service capacity (~1000 req/s single instance)
- **Database load**: 1 query per authenticated request

### Phase B (With Redis Cache)
- **Latency per request**: +2-5ms (cache hit), +5-15ms (cache miss)
- **Cache hit rate**: Expected ~90-95% in steady state
- **Database load**: Reduced by ~90% (only cache misses)
- **Throughput**: ~5000-10000 req/s (limited by Redis, not DB)

---

## Future Enhancements

### Short Term
- [ ] Add Prometheus metrics for authz service
- [ ] Implement circuit breaker for authz calls
- [ ] Add request rate limiting per user
- [ ] Health check includes Redis connectivity

### Medium Term
- [ ] Real PostgreSQL connection
- [ ] Connection pooling (pgbouncer)
- [ ] Cache invalidation on role changes
- [ ] Multi-level caching (in-memory + Redis)

### Long Term
- [ ] gRPC protocol option (performance)
- [ ] Distributed tracing integration
- [ ] Role hierarchy and permissions
- [ ] Policy-based authorization (OPA integration)

---

## Success Criteria

### Phase A
- ✅ All existing integration tests pass
- ✅ Roles come from authz service (verified in logs)
- ✅ Unknown users blocked (403 Forbidden)
- ✅ Latency increase < 20ms per request
- ✅ No changes needed to customer/product services

### Phase B
- ✅ Cache hit rate > 85%
- ✅ Database queries reduced by > 80%
- ✅ Latency improvement vs Phase A
- ✅ Cache expiration works correctly
- ✅ System remains stable under load

---

## Contact & References

**Implementation Owner**: Development Team  
**Architecture Review**: Completed November 5, 2025  
**Related Documents**:
- [System Architecture](../architecture/system-architecture.md)
- [Security Guide](../security/security-guide.md)
- [API Documentation](../api/README.md)

---

*This document is a living plan and will be updated as implementation progresses.*
