# Keycloak Security Quick Reference

## Client Secrets (Development - CHANGE IN PRODUCTION!)

| Client | Secret | Type |
|--------|--------|------|
| **api-gateway** | `gateway-secret-change-in-production` | Confidential |
| **customer-service** | `customer-service-secret-change-in-production` | Bearer-Only |
| **product-service** | `product-service-secret-change-in-production` | Bearer-Only |
| **test-client** | (none) | Public? |

---

## Authentication Examples

### 1. Get Token with test-client (Public - No Secret)
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

### 2. Get Token with api-gateway (Confidential - Requires Secret)
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=api-gateway" \
  -d "client_secret=gateway-secret-change-in-production" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

### 3. Service-to-Service Authentication
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=customer-service" \
  -d "client_secret=customer-service-secret-change-in-production" \
  -d "grant_type=client_credentials"
```

### 4. Use Token to Access Protected Endpoint
```bash
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI..."
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
```

---

## Security Tests

### Test 1: Client Secret Required
```bash
# Should FAIL (no secret):
curl -X POST .../token -d "client_id=api-gateway" -d "grant_type=client_credentials"

# Should SUCCEED (with secret):
curl -X POST .../token \
  -d "client_id=api-gateway" \
  -d "client_secret=gateway-secret-change-in-production" \
  -d "grant_type=client_credentials"
```

### Test 2: Redirect URI Validation
```bash
# Valid redirects only:
- http://localhost:8080/*
- http://localhost:8080/callback
- http://127.0.0.1:8080/*

# All others will be REJECTED
```

---

## Generate Secure Secrets

### Linux/Mac
```bash
openssl rand -base64 32
```

### Windows PowerShell
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

### Using Rotation Script
```bash
# Linux/Mac:
./scripts/rotate-secrets.sh

# Windows:
.\scripts\rotate-secrets.ps1
```

---

## Production Checklist

**Before going to production:**
- [ ] Change ALL client secrets
- [ ] Disable `test-client` (set `enabled: false`)
- [ ] Update redirect URIs to production domains
- [ ] Enable SSL/TLS (`sslRequired: "external"`)
- [ ] Use PostgreSQL database
- [ ] Store secrets in secure vault
- [ ] Enable audit logging
- [ ] Configure monitoring

---

## Emergency Secret Rotation

If secrets are compromised:

1. **Generate new secrets:**
   ```bash
   openssl rand -base64 32
   ```

2. **Update in Keycloak:**
   - Use rotation script OR
   - Admin Console Clients [Client] Credentials Regenerate

3. **Update environment variables:**
 ```bash
   # Update .env file
   API_GATEWAY_CLIENT_SECRET=new-secret-here
   ```

4. **Restart services:**
   ```bash
   docker-compose restart
   ```

5. **Verify:**
   ```bash
   # Test with new secret
   curl -X POST ... -d "client_secret=NEW_SECRET"
   ```

---

## Common Errors

### "Invalid client credentials"
**Cause:** Wrong or missing client secret  
**Fix:** Verify secret is correct and included in request

### "Invalid redirect_uri"
**Cause:** URI not in whitelist  
**Fix:** Add URI to client's `redirectUris` array

### "401 Unauthorized"
**Cause:** Token expired or invalid  
**Fix:** Get new token (tokens expire after 5 minutes by default)

---

## Client Types Explained

### Confidential Client (api-gateway)
- **Has secret:** Yes
- **Can issue tokens:** Yes
- **Can validate tokens:** Yes
- **Use case:** Gateway, web apps

### Bearer-Only Client (customer/product-service)
- **Has secret:** Yes (for service-to-service)
- **Can issue tokens:** No
- **Can validate tokens:** Yes
- **Use case:** Backend services, APIs

### Public Client (test-client)
- **Has secret:** No
- **Can issue tokens:** Yes
- **Can validate tokens:** Yes
- **Use case:** Development/testing only

---

## Resources

- **Full Security Guide:** [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
- **Setup Guide:** [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md)
- **Implementation Summary:** [SECURITY_FIXES_SUMMARY.md](SECURITY_FIXES_SUMMARY.md)
- **Keycloak Docs:** https://www.keycloak.org/documentation

---

**REMEMBER:**
- **NEVER** commit secrets to git
- **ALWAYS** use environment variables for secrets
- **DISABLE** test-client in production
- **ROTATE** secrets regularly
- **MONITOR** for suspicious activity

---

*Quick Reference Card - Keep handy during development*
