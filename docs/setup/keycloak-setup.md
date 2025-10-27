# Keycloak Integration - Quick Start Guide

## Getting Started

### 1. Start All Services
```bash
docker-compose up -d --build
```

### 2. Wait for Keycloak to be Ready
Monitor the logs to ensure Keycloak is fully started:
```bash
docker-compose logs -f keycloak
```
Wait until you see: "Keycloak ... started"

### 3. Access Keycloak Admin Console
- **URL**: http://localhost:8180
- **Username:** admin
- **Password:** admin

## Security Notice

**All confidential clients now require client secrets!**

This configuration includes the following security improvements:
- [x] Client secrets for all confidential clients
- [x] Restricted redirect URIs (no wildcards)
- [x] Restricted web origins
- [x] Service-to-service authentication support

**For detailed security information, see [SECURITY_GUIDE.md](SECURITY_GUIDE.md)**

## Testing Authentication

### Notes for Testing
- Running *curl* in PowerShell masks real *curl.exe*. To remove the alias, run: `Remove-Item Alias:curl`
- Alternatively, you can install wsl using Ubuntu distribution and run the commands there.

### Option 1: Get Access Token Using test-client (Development Only)

**WARNING:** `test-client` is a public client (no secret required). Use only for development!

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=test-client" \
 -d "username=testuser" \
 -d "password=testpass" \
 -d "grant_type=password"
```

**Response:**
```json
{
 "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI...",
 "expires_in":300,
 "refresh_expires_in":1800,
 "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
 "token_type": "Bearer"
}
```

### Option 2: Using api-gateway Client (With Client Secret)

**This is the secure way - requires client secret:**

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=api-gateway" \
 -d "client_secret=gateway-secret-change-in-production" \
 -d "username=testuser" \
 -d "password=testpass" \
 -d "grant_type=password"
```

### Option 3: Using Admin User

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=test-client" \
 -d "username=adminuser" \
 -d "password=adminpass" \
 -d "grant_type=password"
```

### Option 4: Service-to-Service Authentication (Client Credentials)

**New! Services can authenticate themselves:**

```bash
# Customer service authenticates itself
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=customer-service" \
 -d "client_secret=customer-service-secret-change-in-production" \
 -d "grant_type=client_credentials"
```

## Testing Protected Endpoints

### 1. Try Accessing Without Token (Should Fail)
```bash
curl -v http://localhost:8080/customers
```
**Expected:**401 Unauthorized - Jwt is missing

### 2. Access With Valid Token (Should Succeed)
```bash
# First, get the token and extract it
TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=test-client" \
 -d "username=testuser" \
 -d "password=testpass" \
 -d "grant_type=password" | jq -r '.access_token')

# Use the token to access protected endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
```

### 3. Test Product Service
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/products
```

### 4. Test Client Secret Enforcement

**This should FAIL (no secret provided):**
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=api-gateway" \
 -d "grant_type=client_credentials"
```
**Expected:**401 Unauthorized - Invalid client credentials

**This should SUCCEED (with secret):**
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=api-gateway" \
 -d "client_secret=gateway-secret-change-in-production" \
 -d "grant_type=client_credentials"
```
**Expected:** Valid access token

## Verifying JWT Token

You can decode and verify your JWT token at https://jwt.io or using:

```bash
# Decode JWT (requires jq)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

**Expected claims:**
```json
{
  "exp": 1761529888,
  "iat": 1761529588,
  "jti": "onrtro:f5c157db-fae7-c91c-9be1-6743885440ca",
  "iss": "http://localhost:8180/realms/api-gateway-poc",
  "sub": "ff7c5cc6-7c87-4f47-94af-f51a641dbbec",
  "typ": "Bearer",
  "azp": "test-client",
  "sid": "d1646165-67e7-5dbf-72c7-2c1b563aaba9",
  "acr": "1",
  "allowed-origins": [
    "http://127.0.0.1:*",
    "http://localhost:*"
  ],
  "realm_access": {
    "roles": [
      "user"
    ]
  },
  "scope": "profile email",
  "email_verified": true,
  "name": "Test User",
  "preferred_username": "testuser",
  "given_name": "Test",
  "family_name": "User",
  "email": "testuser@example.com"
}
```

## Client Secrets Reference

**FOR DEVELOPMENT ONLY - CHANGE IN PRODUCTION!**

| Client | Secret | Type |
|--------|--------|------|
| api-gateway | `gateway-secret-change-in-production` | Confidential |
| customer-service | `customer-service-secret-change-in-production` | Bearer-Only |
| product-service | `product-service-secret-change-in-production` | Bearer-Only |
| test-client | (none) | Public |

**Generate secure secrets for production:**
```bash
openssl rand -base6432
```

## Available Test Users

| Username | Password | Roles |
|-------------|------------|------------------------------------------------|
| testuserUNV | testpass | unverified-user |
| testuser | testpass | user |
| adminuser | adminpass | user, admin, customer-manager, product-manager |
| testuserCM | testpass | user, customer-manager |
| testuserPM | testpass | user, product-manager |
| testuserPCM | testpass | user, product-category-manager |

**NOTE**: unverified-user means they have a login but haven't been verified to get any roles.
This is separate from guest users who have no login at all.

## Useful Commands

### View All Service Logs
```bash
docker-compose logs -f
```

### View Keycloak Logs Only
```bash
docker-compose logs -f keycloak
```

### View Gateway Logs Only
```bash
docker-compose logs -f gateway
```

### Restart Keycloak
```bash
docker-compose restart keycloak
```

### Stop All Services
```bash
docker-compose down
```

### Rebuild and Restart
```bash
docker-compose down
docker-compose up -d --build
```

## Important Endpoints

### Keycloak
- **Admin Console**: http://localhost:8180
- **Realm Info**: http://localhost:8180/realms/api-gateway-poc
- **Token Endpoint**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token
- **JWKS (Public Keys)**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/certs
- **UserInfo**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/userinfo

### API Gateway
- **Gateway**: http://localhost:8080
- **Admin Interface**: http://localhost:9901

### Services (Direct Access - Bypass Gateway)
- **Customer Service**: http://localhost:8001
- **Product Service**: http://localhost:8002

## Troubleshooting

### Issue: "401 Unauthorized" even with token
**Solutions:**
1. Verify the user has RBAC roles required by the endpoint
2. Verify token hasn't expired (default:5 minutes)
3. Check that Keycloak is accessible from gateway container:
 ```bash
 docker-compose exec gateway ping keycloak
 ```
4. Verify JWKS endpoint is accessible:
 ```bash
 docker-compose exec gateway curl http://keycloak:8080/realms/api-gateway-poc/protocol/openid-connect/certs
 ```

### Issue: "Invalid client credentials"
**Solutions:**
1. Verify you're using the correct client secret
2. Check that the client is not public (`publicClient: false`)
3. Ensure `serviceAccountsEnabled: true` for client credentials flow
4. Verify client ID is correct

### Issue: "Invalid redirect_uri"
**Solutions:**
1. Check that redirect URI matches exactly (including trailing slashes)
2. Verify URI is in the client's allowed redirect URIs list
3. For development, use `http://localhost:8080/*`

### Issue: Keycloak container exits immediately
**Solutions:**
1. Check logs: `docker-compose logs keycloak`
2. Verify port8180 is not in use
3. Ensure realm-export.json is valid JSON

### Issue: Gateway can't validate tokens
**Solutions:**
1. Wait for Keycloak health check to pass
2. Check gateway logs for JWT filter errors
3. Verify Envoy configuration syntax
4. Ensure JWKS endpoint is accessible from gateway

### Issue: Services not starting
**Solutions:**
1. Check if all required ports are available
2. Ensure Docker has enough resources
3. Review individual service logs

## Security Best Practices

### For Development
- Use `test-client` for easy testing (no secret required)
- Use the provided default secrets
- Test on localhost only

### For Production
- NEVER use these default secrets!
- DISABLE test-client!
- Generate cryptographically secure secrets
- Use environment variables for secrets
- Implement secrets management (Azure Key Vault, AWS Secrets Manager)
- Enable HTTPS/TLS
- Use PostgreSQL database
- Configure proper hostname
- Enable comprehensive audit logging
- Implement rate limiting

**See [SECURITY_GUIDE.md](SECURITY_GUIDE.md) for complete security documentation.**

## Next Steps

1. **Understand Security Model**
 - Review [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
 - Understand client types (confidential vs public vs bearer-only)
 - Learn about OAuth2.0 flows

2. **Implement Role-Based Access Control (RBAC)**
 - Add role checks in Envoy configuration
 - Implement fine-grained authorization in services

3. **Add Service-to-Service Authentication**
 - Configure services to use client credentials flow
 - Implement token validation in backend services

4. **Production Hardening**
 - Change all client secrets
 - Disable test-client
 - Add PostgreSQL for Keycloak
 - Enable HTTPS/TLS
 - Configure proper secrets management
 - Set up monitoring and alerting

5. **Advanced Features**
- Social login integration
 - Multi-factor authentication
 - Custom themes
 - User federation (LDAP/Active Directory)

## Additional Resources

- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Complete security documentation
- [services/keycloak/README.md](services/keycloak/README.md) - Keycloak service details
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Specification](https://openid.net/connect/)
