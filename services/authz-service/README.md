# Authorization Service

External authorization service for role-based access control with Redis caching.

## Overview

The authorization service is called by Envoy's `ext_authz` filter for each authenticated request. It:
1. Extracts user email from the JWT token
2. Checks Redis cache for roles (5-minute TTL)
3. On cache miss, looks up roles from database (currently mocked)
4. Caches result in Redis for future requests
5. Returns roles in response headers for RBAC decisions

## Architecture

```
Envoy → ext_authz → /authz/roles → AuthZ Service → Redis Cache → Database (mock)
                                   ↓
                                   Returns: x-user-email, x-user-roles headers
```

**React UI Integration:**
```
React → /auth/me → AuthZ Service → Redis/Database
                  ↓
                  Returns: { email, roles } JSON
```

## API Endpoints

### Health Check
```http
GET /authz/health

Response: 200 OK
{
  "status": "healthy",
  "service": "authz-service",
  "version": "1.0.0",
  "cache_enabled": true,
  "cache_healthy": true
}
```

### Role Lookup (Internal - Envoy ext_authz only)
```http
POST /authz/roles

Request Headers:
  Authorization: Bearer <jwt-token>
  X-Request-Id: <uuid>

Response: 200 OK
Headers:
  x-user-email: testuser@example.com
  x-user-roles: user,customer-manager
Body: (empty)
```

### User Info (Public - React UI)
```http
GET /authz/me

Request Headers:
  Authorization: Bearer <jwt-token>

Response: 200 OK
{
  "email": "testuser@example.com",
  "roles": ["user", "customer-manager"]
}
```

## User Database (Mock)

Current mock users and their roles:

| Email | Roles | Access Level |
|-------|-------|--------------|
| test.user-unvrfd@example.com | unverified-user | Very limited access (Email not verified) |
| test.user-vrfd@example.com | verified-user | Limited access (Email verified, incomplete profile) |
| test.user@example.com | user | Basic access (profile completed) |
| test.user-cm@example.com | user, customer-manager | Can manage customers |
| test.user-pm@example.com | user, product-manager | Can manage products |
| test.user-pcm@example.com | user, product-category-manager | Can manage products in the category they are responsible for |
| admin.user@example.com | user, admin| System management |

## Configuration

Environment variables:

- `SERVICE_PORT`: Port to listen on (default: 9000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `SERVICE_NAME`: Service name for logging (default: authz-service)
- `REDIS_URL`: Redis connection URL (e.g., redis://redis:6379)
- `REDIS_TTL`: Cache TTL in seconds (default: 300)

## Security

- **Network Isolation**: Service is NOT exposed to host, only accessible via internal Docker network
- **JWT Validation**: JWT signature already validated by Envoy before calling this service
- **Fail Closed**: Envoy configured with `failure_mode_allow: false`

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
SERVICE_PORT=9000 python main.py
```

### Testing

```bash
# Unit tests
pytest tests/test_authz_service.py

# Integration tests
pytest tests/integration/test_external_authz.py
```

### Debugging

Check logs for role lookup operations:

```bash
# View authz service logs
docker-compose logs -f authz-service

# Filter for specific user
docker-compose logs authz-service | grep "testuser@example.com"
```

## Redis Caching

**Status:** Implemented and Active

- **Cache Key Format:** `user:platform-roles:{email}`
- **TTL:** 300 seconds (5 minutes)
- **Strategy:** Cache-aside (check cache, fallback to database)
- **Expected Hit Rate:** 90-95%

**Cache Behavior:**
- First request: Cache miss → database lookup → cache result
- Subsequent requests: Cache hit → return cached roles
- After 5 minutes: Cache expired → refresh from database

**Monitoring:**
```bash
# View cache hits/misses in logs
docker-compose logs authz-service | grep "Cache HIT\|Cache MISS"

# PowerShell
docker-compose logs authz-service | Select-String "Cache HIT|Cache MISS"
```

## Common Tasks

### Add New User Roles

Edit `authz_data_access.py`:
```python
USER_ROLES_DB = {
    "test.user@example.com": ["user"],
    # Add new user here
    "newuser@example.com": ["user", "customer-manager"],
}
```

Rebuild service:
```bash
docker-compose up -d --build authz-service
```

### Test Authentication Flow

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client&username=testuser&password=testpass&grant_type=password" \
  | jq -r '.access_token')

# Test /auth/me endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/auth/me

# Test protected API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
```

## Future Enhancements

- [ ] Real PostgreSQL connection
- [ ] Connection pooling
- [ ] Role management API (admin)
- [ ] Prometheus metrics
- [ ] Distributed tracing
- [ ] Circuit breaker pattern

## Related Documentation

- [System Architecture](../../docs/architecture/system-architecture.md)
- [Authentication & Authorization Flow](../../docs/architecture/authentication-authorization-flow.md)
- [Security Guide](../../docs/security/security-guide.md)
