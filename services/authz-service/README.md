# Authorization Service

External authorization service for role-based access control. This service provides user role lookups based on email addresses extracted from JWT tokens.

## Overview

The authorization service is called by Envoy's `ext_authz` filter for each authenticated request. It:
1. Extracts user email from the JWT token
2. Looks up roles from PostgreSQL (currently mocked)
3. Returns roles in response headers
4. Envoy uses these roles for RBAC authorization decisions

## Architecture

```
Envoy → ext_authz → /authz/roles → AuthZ Service → PostgreSQL (mock)
                                   ↓
                                   Returns: X-User-Roles header
```

## API Endpoints

### Health Check
```http
GET /authz/health

Response: 200 OK
{
  "status": "healthy",
  "service": "authz-service",
  "version": "1.0.0"
}
```

### Role Lookup
```http
POST /authz/roles

Request Headers:
  Authorization: Bearer <jwt-token>
  X-Request-Id: <uuid>

Response: 200 OK
Headers:
  X-User-Email: testuser@example.com
  X-User-Roles: user,customer-manager
Body: (empty)
```

## User Database (Mock)

Current mock users and their roles:

| Email | Roles | Access Level |
|-------|-------|--------------|
| test.user-unvrfd@example.com | unverified-user | Very limited accees (Email not verified) |
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

## Phase B: Redis Caching

In Phase B, Redis caching will be added to improve performance:
- Cache key: `user:roles:{email}`
- Cache TTL: 300 seconds (5 minutes)
- Cache hit rate expected: 90-95%

See [Implementation Plan](../../docs/development/external-authz-implementation-plan.md) for details.

## Future Enhancements

- [ ] Real PostgreSQL connection
- [ ] Connection pooling
- [ ] Redis caching (Phase B)
- [ ] Prometheus metrics
- [ ] Distributed tracing
- [ ] Circuit breaker pattern

## Related Documentation

- [Implementation Plan](../../docs/development/external-authz-implementation-plan.md)
- [System Architecture](../../docs/architecture/system-architecture.md)
- [Security Guide](../../docs/security/security-guide.md)
