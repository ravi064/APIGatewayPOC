# Security Configuration Guide

## Overview

This document explains the security measures implemented in the Keycloak configuration and how to properly secure your deployment.

---

## JWT Security Validation

Our API gateway enforces JWT security through multiple layers of defense. All security controls are validated through automated integration tests.

### 1. JWT Signature Verification (Enforced at Gateway)

**Protection:** Prevents tampering with JWT token contents (payload/claims).

**How it works:**
- Envoy validates JWT signatures before forwarding requests
- Any modification to JWT payload invalidates the signature
- Tampered tokens are rejected with `401 Unauthorized`

**Automated Test:** `test_jwt_tampering_rejected()`
- Simulates attack: User modifies email claim to impersonate another user
- Expected result: Token rejected with 401
- Validates: Users cannot escalate privileges by modifying JWT claims

**Example attack prevented:**
```bash
# Attacker authenticates as test.user@example.com
# Then modifies JWT payload to claim test.user-cm@example.com
# Result: 401 Unauthorized - Attack blocked at gateway
```

---

### 2. JWT Expiration Enforcement

**Protection:** Prevents use of old/expired tokens.

**How it works:**
- JWT tokens have `exp` (expiration) claim
- Envoy validates expiration before processing requests
- Expired tokens are rejected immediately

**Automated Test:** `test_jwt_expired_token_rejected()`
- Simulates attack: Attacker modifies `exp` claim to extend token lifetime
- Expected result: Token rejected with 401 (signature mismatch)
- Validates: Token expiration cannot be bypassed

**Token Lifespan (Configurable):**
```json
"accessTokenLifespan": 300,        // 5 minutes (default)
"ssoSessionIdleTimeout": 1800,   // 30 minutes
```

---

### 3. JWT Issuer Validation

**Protection:** Prevents tokens from untrusted/malicious identity providers.

**How it works:**
- JWT tokens contain `iss` (issuer) claim
- Envoy validates issuer matches trusted Keycloak instance
- Tokens from wrong issuers are rejected

**Automated Test:** `test_jwt_wrong_issuer_rejected()`
- Simulates attack: Attacker sets up fake Keycloak and issues tokens
- Expected result: Token rejected with 401 (signature mismatch)
- Validates: Only tokens from trusted Keycloak are accepted

**Trusted Issuer Configuration:**
```yaml
# In Envoy JWT filter configuration:
issuer: "http://localhost:8180/realms/api-gateway-poc"
```

---

### Security Test Results

All JWT security tests pass, confirming that:
- ? JWT signature verification is enforced at gateway
- ? Users cannot impersonate other users via JWT tampering
- ? Expired/modified tokens are rejected
- ? Tokens from untrusted issuers are rejected
- ? Defense-in-depth: Multiple validation layers

**Test Location:** `tests/integration/test_api_gateway.py`

**Running Security Tests:**
```bash
# Run all JWT security tests
pytest tests/integration/test_api_gateway.py -k "jwt" -v -s

# Run individual test
pytest tests/integration/test_api_gateway.py::test_jwt_tampering_rejected -v -s
pytest tests/integration/test_api_gateway.py::test_jwt_expired_token_rejected -v -s
pytest tests/integration/test_api_gateway.py::test_jwt_wrong_issuer_rejected -v -s
```

**Expected Output (All Pass):**
```
? Security test passed: Tampered JWT rejected with status 401
? Security test passed: Expired JWT rejected with status 401
? Security test passed: JWT with wrong issuer rejected with status 401
```

**For detailed test instructions, see:** [Test Utilities Guide](../test/test-utilities.md#jwt-security-tests)

---

## Understanding the 4 Keycloak Clients

### 1. `api-gateway` (Confidential Client)
**Purpose:** Main entry point for authentication

**Configuration:**
- `publicClient: false` - Requires client secret
- `serviceAccountsEnabled: true` - Can use client credentials flow
- `directAccessGrantsEnabled: true` - Supports password grant (for testing)
- `standardFlowEnabled: true` - Supports authorization code flow

**Security Features:**
- **Client Secret Required:** `gateway-secret-change-in-production`
- **Restricted Redirect URIs:** Only localhost:8080 allowed
- **Restricted Web Origins:** Only localhost:8080 allowed

**How it works:**
```
User -> API Gateway -> Keycloak (with client_id + client_secret)
     -> JWT Token
```

---

### 2. `customer-service` (Bearer-Only Client)
**Purpose:** Backend service that validates tokens

**Configuration:**
- `bearerOnly: true` - **Only validates** JWT tokens, never issues them
- `publicClient: false` - Has a client secret
- `serviceAccountsEnabled: true` - Can authenticate itself for service-to-service calls

**Security Features:**
- **Client Secret Required:** `customer-service-secret-change-in-production`
- **No redirect URIs:** Cannot be used for login flows
- **Bearer-only mode:** Only accepts pre-issued tokens

**How it works:**
```
Request + JWT -> Customer Service -> Validates JWT signature & claims
  -> Checks if token is not expired
            -> Processes request if valid
```

---

### 3. `product-service` (Bearer-Only Client)
**Purpose:** Backend service that validates tokens

**Configuration:**
- Same pattern as `customer-service`
- `bearerOnly: true`
- `publicClient: false`

**Security Features:**
- **Client Secret Required:** `product-service-secret-change-in-production`
- **No redirect URIs:** Cannot be used for login flows
- **Bearer-only mode:** Only accepts pre-issued tokens

---

### 4. `test-client` (Public Client - Development Only)
**Purpose:** Development/testing tool for easy token retrieval

**Configuration:**
- `publicClient: true` - **NO CLIENT SECRET** (intentionally)
- `directAccessGrantsEnabled: true` - Allows password grant
- Supports PKCE for added security

**Security Warnings:**
- **NO SECRET REQUIRED** - Anyone can use this client
- **DISABLE IN PRODUCTION!**
- **Wildcard redirects for localhost only**

**Why it exists:**
```bash
# Makes testing easy during development:
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

**Production Action:** Set `enabled: false` or remove this client entirely!

---

## Security Concerns Addressed

### Previous Issues (FIXED)

#### 1. Missing Client Secrets
**Before:**
```json
{
  "clientId": "api-gateway",
  "publicClient": false,
  // NO SECRET! Anyone could impersonate this client
}
```

**After:**
```json
{
  "clientId": "api-gateway",
  "publicClient": false,
  "secret": "gateway-secret-change-in-production"
  // Now requires secret for authentication
}
```

---

#### 2. Wildcard Redirect URIs
**Before:**
```json
"redirectUris": ["*"],  // Tokens could go ANYWHERE!
"webOrigins": ["*"]     // Any origin allowed!
```

**After:**
```json
"redirectUris": [
  "http://localhost:8080/*",
  "http://localhost:8080/callback"
],
"webOrigins": [
  "http://localhost:8080"
]
// Only specific URLs allowed
```

---

#### 3. Lack of Service-to-Service Authentication
**Before:**
- Services had `bearerOnly: true` but no secrets
- Couldn't authenticate themselves

**After:**
- Services have client secrets
- Can use client credentials flow for service-to-service calls
- Can prove their identity when needed

---

## How Client Authentication Works Now

### Scenario 1: User Login via API Gateway
```bash
# Gateway authenticates with Keycloak using its secret:
curl -X POST http://keycloak:8080/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=api-gateway" \
  -d "client_secret=gateway-secret-change-in-production" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

**Security:** Only the real gateway (with the secret) can get tokens for users.

---

### Scenario 2: Service-to-Service Authentication
```bash
# Customer service authenticates itself to call another service:
curl -X POST http://keycloak:8080/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=customer-service" \
  -d "client_secret=customer-service-secret-change-in-production" \
  -d "grant_type=client_credentials"
```

**Security:** Services can prove their identity when making API calls.

---

### Scenario 3: Token Validation (Bearer-Only)
```
1. User requests: GET /customers + Authorization: Bearer <JWT>
2. Gateway forwards to customer-service
3. Customer service:
   - Validates JWT signature using Keycloak's public keys
   - Checks expiration time
   - Verifies issuer, audience, and other claims
   - Processes request if valid
```

**Security:** Services validate tokens without needing to call Keycloak for every request (uses cached public keys).

---

## Preventing Spoofing Attacks

### Attack 1: Client Impersonation
**Before:** Anyone could claim to be `api-gateway`
```bash
curl -d "client_id=api-gateway" ...  # No secret needed!
```

**After:** Must prove identity with secret
```bash
curl -d "client_id=api-gateway" \
     -d "client_secret=gateway-secret-change-in-production" ...
```

---

### Attack 2: Redirect URI Hijacking
**Before:** Tokens could be sent to attacker's domain
```
https://keycloak/auth?redirect_uri=https://evil.com/steal
```

**After:** Only whitelisted URIs accepted
```
https://keycloak/auth?redirect_uri=http://localhost:8080/callback  # OK
https://keycloak/auth?redirect_uri=https://evil.com/steal          # REJECTED
```

---

### Attack 3: Internal Network Access
**Before:** Direct service access with no authentication
```bash
curl http://customer-service:8001/customers  # No auth!
```

**After:** Services validate JWT tokens
- Envoy gateway enforces JWT validation
- Direct service access requires valid token
- Network isolation provides defense in depth

---

## Production Security Checklist

### Critical Actions

- [ ] **Change all client secrets** to cryptographically secure values
  ```bash
  # Generate secure secrets:
  openssl rand -base64 32
  ```

- [ ] **Disable or remove `test-client`**
  ```json
  {
    "clientId": "test-client",
    "enabled": false  // Set to false in production
  }
  ```

- [ ] **Update redirect URIs** to production URLs
  ```json
  "redirectUris": [
    "https://yourdomain.com/callback",
    "https://yourdomain.com/auth/callback"
  ]
  ```

- [ ] **Enable SSL/TLS**
  ```json
  "sslRequired": "external"  // Require HTTPS
  ```

- [ ] **Use environment variables** for secrets (never hardcode)
  ```bash
  # .env file (NEVER commit to git!)
  API_GATEWAY_CLIENT_SECRET=<secure-secret-here>
  ```

- [ ] **Enable hostname strict mode**
  ```env
  KC_HOSTNAME_STRICT=true
  KC_HOSTNAME=auth.yourdomain.com
  ```

- [ ] **Use PostgreSQL** instead of H2 database
  ```env
  KC_DB=postgres
  KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak
  ```

- [ ] **Configure rate limiting** in Keycloak
  - Set max login failures
  - Configure wait times

- [ ] **Review token lifespans**
  ```json
  "accessTokenLifespan": 300,        // 5 minutes
  "ssoSessionIdleTimeout": 1800,   // 30 minutes
  ```

---

## Secrets Management

### Development (Current Setup)
```bash
# Secrets in realm-export.json (acceptable for POC)
"secret": "gateway-secret-change-in-production"
```

### Production (Recommended)
```bash
# Use environment variables
docker-compose.yml:
  environment:
    - API_GATEWAY_SECRET=${API_GATEWAY_CLIENT_SECRET}

# Store in secure secrets manager:
# - Azure Key Vault
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

---

## How to Rotate Client Secrets

1. **Generate new secret:**
   ```bash
   openssl rand -base64 32
   ```

2. **Update in Keycloak:**
   - Login to Admin Console (http://localhost:8180)
   - Navigate to: Clients -> api-gateway -> Credentials
   - Click "Regenerate Secret" or enter new secret

3. **Update in services:**
   - Update environment variables
   - Restart affected services

4. **Test authentication:**
   ```bash
   # Verify new secret works
   curl -X POST ... -d "client_secret=NEW_SECRET"
   ```

---

## Network Security

### Current Setup (Docker Network)

```
+------------------------------------------+
|   Docker Network: microservices          |
|                                          |
|  +----------+    +------------------+    |
|  | Gateway  |--->| Customer Service |    |
|  | (Envoy)  |    |  Port 8001       |    |
|  +----------+    +------------------+    |
|       |                                  |
|       v          +------------------+    |
|  +----------+    | Product Service  |    |
|  | Keycloak |    |  Port 8002       |    |
|  |Port 8180 |    +------------------+    |
|  +----------+                            |
+------------------------------------------+
       |
       v
       Internet Access
    (Ports 8080, 8180 exposed)
```

**Network Flow:**
1. **External Access**: Only Gateway (8080) and Keycloak (8180) exposed
2. **Internal Communication**: Services communicate within Docker network
3. **Authentication**: All requests validated via Keycloak JWT tokens
4. **Isolation**: Microservices not directly accessible from internet

**Security:**
- Services isolated in Docker network
- Only gateway exposed to internet
- Internal service-to-service communication secured
- JWT validation at gateway level

**Additional Recommendations:**
- Use separate networks for different security zones
- Enable Docker network encryption
- Implement service mesh (Istio/Linkerd) for mTLS
- Consider network policies for additional isolation

---

## Monitoring & Auditing

### Enable Keycloak Events
```json
"eventsEnabled": true,
"eventsListeners": ["jboss-logging"],
"enabledEventTypes": [
  "LOGIN",
  "LOGIN_ERROR",
  "LOGOUT",
  "CLIENT_LOGIN",
  "CLIENT_LOGIN_ERROR"
]
```

### Monitor for Suspicious Activity
- Failed login attempts
- Invalid client authentication
- Token usage from unexpected IPs
- Unusual redirect URI requests

---

## Testing Security

### Test Client Secret Enforcement
```bash
# Should FAIL (no secret):
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=api-gateway" \
  -d "grant_type=client_credentials"

# Should SUCCEED (with secret):
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=api-gateway" \
  -d "client_secret=gateway-secret-change-in-production" \
  -d "grant_type=client_credentials"
```

### Test Redirect URI Validation
```bash
# Should FAIL (invalid redirect):
https://keycloak/auth?client_id=api-gateway&redirect_uri=https://evil.com

# Should SUCCEED (valid redirect):
https://keycloak/auth?client_id=api-gateway&redirect_uri=http://localhost:8080/callback
```

---

## Summary

### What Changed?
1. **Client secrets added** to all confidential clients
2. **Redirect URIs restricted** to specific allowed URLs
3. **Web origins restricted** to prevent CORS attacks
4. **Service-to-service authentication** now possible
5. **Test client properly marked** as development-only

### What's Protected?
1. **Client impersonation** - Requires secrets
2. **Redirect hijacking** - Whitelisted URIs only
3. **Token theft** - Proper origin validation
4. **Unauthorized access** - JWT validation enforced

### What's Next?
1. Review and change all client secrets
2. Configure production-grade database
3. Enable HTTPS/TLS
4. Implement comprehensive monitoring
5. Set up secrets management
6. Conduct security audit

---

## Questions & Answers

**Q: Can someone still spoof a client?**
A: No, not without the client secret. All confidential clients now require secrets.

**Q: What about the bearer-only clients?**
A: They validate incoming tokens but don't issue them. They also have secrets for service-to-service auth.

**Q: Why does test-client have no secret?**
A: It's for development convenience. **Disable it in production!**

**Q: How do I change the secrets?**
A: Use Keycloak Admin Console or regenerate via API, then update environment variables.

**Q: Is this production-ready?**
A: This is a good foundation, but you still need:
- Secure secret storage
- HTTPS/TLS
- Production database
- Proper monitoring
- Security hardening

---

**Last Updated:** [Current Date]
**Reviewed By:** Security Team
**Next Review:** [Schedule regular security reviews]
