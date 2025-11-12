# Security Quick Start

Concise security guide for the API Gateway POC.

## Authentication Flow

```
User → Keycloak (JWT) → Gateway (Validate JWT) → AuthZ Service (Roles) → Backend
```

1. User logs in to Keycloak, receives JWT token
2. Gateway validates JWT signature and expiration
3. AuthZ service looks up user roles (from database + Redis cache)
4. Backend services receive roles in headers for authorization decisions

## Get Started in 3 Steps

### 1. Get JWT Token

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

**Returns:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 300
}
```

### 2. Call Protected API

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8080/customers
```

### 3. Refresh Expired Token

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=<refresh_token>"
```

## Available Roles

| Role | Access Level |
|------|--------------|
| `guest` | Unauthenticated (no JWT) |
| `unverified-user` | Authenticated but no roles assigned |
| `user` | Basic authenticated access |
| `customer-manager` | Can manage customer data |
| `product-manager` | Can manage product catalog |

## Test Users

**Default Keycloak Users:**
- `testuser` / `testpass` - Has `user` role in authz service

**Create Additional Users:**
1. Go to http://localhost:8180 (admin/admin)
2. Navigate to Users → Add User
3. Set username, email, password
4. Add corresponding role entry in `services/authz-service/authz_data_access.py`

## Security Best Practices

### Development (Current)
- Default secrets in code (DO NOT use in production)
- JWT tokens expire in 5 minutes
- Roles cached in Redis for 5 minutes
- No SSL/TLS (localhost only)

### Production Checklist
- [ ] Rotate all client secrets (use `scripts/rotate-secrets.sh`)
- [ ] Store secrets in environment variables or vault
- [ ] Enable SSL/TLS (`sslRequired: "external"`)
- [ ] Use PostgreSQL for authz database
- [ ] Disable test-client in Keycloak
- [ ] Configure proper redirect URIs
- [ ] Enable audit logging
- [ ] Set up monitoring and alerting

## Common Errors

**401 Unauthorized**
- Token missing, expired, or invalid
- Get new token and try again

**403 Forbidden**
- User authenticated but lacks required role
- Check user roles in authz service

**Invalid client credentials**
- Wrong or missing client secret
- Verify secret in request matches Keycloak configuration

## Client Types

| Client | Secret Required | Use Case |
|--------|-----------------|----------|
| `test-client` | No | Development/testing only |
| `api-gateway` | Yes | Gateway authentication |
| `customer-service` | Yes | Service-to-service auth |
| `product-service` | Yes | Service-to-service auth |

## Secret Rotation

**Generate new secret:**
```bash
openssl rand -base64 32
```

**Update in Keycloak:**
1. Admin Console → Clients → [Client Name]
2. Credentials tab → Regenerate Secret
3. Copy new secret

**Update environment:**
```bash
# .env file
API_GATEWAY_CLIENT_SECRET=new-secret-here
```

**Restart services:**
```bash
docker-compose restart
```

## Monitoring

**Check service health:**
```bash
curl http://localhost:8080/customers/health
curl http://localhost:8080/products/health
```

**View logs:**
```bash
docker-compose logs -f gateway
docker-compose logs -f authz-service
docker-compose logs -f keycloak
```

**Test authentication:**
```bash
# Should succeed with valid token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers

# Should fail with 401
curl http://localhost:8080/customers
```

## Additional Resources

- [Detailed Security Guide](security-guide.md) - Comprehensive documentation
- [Keycloak Setup](../setup/keycloak-setup.md) - Keycloak configuration
- [React Integration](../development/react-auth-integration.md) - UI authentication

## Quick Commands Reference

```bash
# Start services
docker-compose up -d

# Get token (save as $TOKEN)
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client&username=testuser&password=testpass&grant_type=password" \
  | jq -r '.access_token')

# Test authenticated request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers

# Rotate secrets
./scripts/rotate-secrets.sh

# View service logs
docker-compose logs -f authz-service

# Stop services
docker-compose down
```

---

**Need detailed information?** See [Security Guide](security-guide.md) for comprehensive documentation.
