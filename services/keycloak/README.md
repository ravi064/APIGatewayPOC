# Keycloak Service

This directory contains the Keycloak configuration for the API Gateway POC project.

## Overview

Keycloak is an open-source Identity and Access Management (IAM) solution that provides:
- Single Sign-On (SSO)
- OAuth 2.0 and OpenID Connect support
- User Federation
- Identity Brokering
- Social Login

## Security Notice

**?? IMPORTANT: This configuration includes client secrets for demonstration purposes.**

- All confidential clients now have client secrets
- Redirect URIs are restricted to specific allowed URLs
- The `test-client` is for development only - **DISABLE IN PRODUCTION**
- See [Security Guide](../../docs/security/security-guide.md) for complete security documentation

**Production Requirements:**
- Change all client secrets to cryptographically secure values
- Update redirect URIs to production domains
- Disable or remove the `test-client`
- Enable SSL/TLS
- Use PostgreSQL instead of H2
- Implement secrets management (Azure Key Vault, AWS Secrets Manager, etc.)

## Configuration

### Dockerfile
- Based on the latest official Keycloak image (Quarkus-based)
- Runs in development mode for easier testing
- Automatically imports the realm configuration on startup

### Default Credentials

**Admin Console:**
- URL: http://localhost:8180
- Username: `admin`
- Password: `admin`

**Test Users:**
- Username: `testuser` / Password: `testpass` (roles: user, customer-manager)
- Username: `adminuser` / Password: `adminpass` (roles: user, admin, customer-manager, product-manager)

## Realm Configuration

The `realm-export.json` file contains the pre-configured realm `api-gateway-poc` with:

### Clients

#### 1. api-gateway (Confidential Client)
- **Purpose:** Main gateway client for token issuance
- **Type:** Confidential (requires client secret)
- **Secret:** `gateway-secret-change-in-production` ?? **CHANGE IN PRODUCTION**
- **Flows:** Authorization code, direct grant, client credentials
- **Redirect URIs:** `http://localhost:8080/*` (update for production)
- **Use Case:** Authenticating users and issuing tokens

#### 2. customer-service (Bearer-Only Client)
- **Purpose:** Backend service that validates tokens
- **Type:** Bearer-only (doesn't issue tokens)
- **Secret:** `customer-service-secret-change-in-production` ?? **CHANGE IN PRODUCTION**
- **Use Case:** Validating JWT tokens and service-to-service auth

#### 3. product-service (Bearer-Only Client)
- **Purpose:** Backend service that validates tokens
- **Type:** Bearer-only (doesn't issue tokens)
- **Secret:** `product-service-secret-change-in-production` ?? **CHANGE IN PRODUCTION**
- **Use Case:** Validating JWT tokens and service-to-service auth

#### 4. test-client (Public Client - Development Only)
- **Purpose:** Testing and development tool
- **Type:** Public (no client secret required)
- **?? WARNING:** Disable in production! Anyone can use this client.
- **Redirect URIs:** `http://localhost:*` (development only)
- **Use Case:** Easy token retrieval during development

### Roles
- `user`: Basic user role
- `admin`: Administrator role
- `customer-manager`: Can manage customer data
- `product-manager`: Can manage product data

## Testing Authentication

### Get Access Token (Password Grant)

**Using test-client (Development Only):**
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

**Using api-gateway (With Client Secret):**
```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-gateway" \
  -d "client_secret=gateway-secret-change-in-production" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
```

### Client Credentials Flow (Service-to-Service)

```bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=customer-service" \
  -d "client_secret=customer-service-secret-change-in-production" \
  -d "grant_type=client_credentials"
```

### Access Protected Endpoints

```bash
# Use the access_token from previous call
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8080/customers
```

## Client Secrets Reference

**?? WARNING: Change these secrets before deploying to production!**

Generate secure secrets using:
```bash
openssl rand -base64 32
```

**Current secrets (for development only):**
- **api-gateway:** `gateway-secret-change-in-production`
- **customer-service:** `customer-service-secret-change-in-production`
- **product-service:** `product-service-secret-change-in-production`
- **test-client:** (none - public client)

## Endpoints

- **Admin Console**: http://localhost:8180
- **Realm Endpoint**: http://localhost:8180/realms/api-gateway-poc
- **JWKS Endpoint**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/certs
- **Token Endpoint**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token
- **UserInfo Endpoint**: http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/userinfo

## Environment Variables

The following environment variables are used:

- `KC_BOOTSTRAP_ADMIN_USERNAME`: Admin username (replaces deprecated `KEYCLOAK_ADMIN`)
- `KC_BOOTSTRAP_ADMIN_PASSWORD`: Admin password (replaces deprecated `KEYCLOAK_ADMIN_PASSWORD`)
- `KC_HTTP_PORT`: HTTP port (default: 8080)
- `KC_HOSTNAME_STRICT`: Disable strict hostname checking for development
- `KC_HTTP_ENABLED`: Enable HTTP (not just HTTPS)
- `KC_HEALTH_ENABLED`: Enable health endpoints
- `KC_METRICS_ENABLED`: Enable metrics endpoints

## Security Features

### Implemented
? Client secrets for all confidential clients  
? Restricted redirect URIs (no wildcards except test-client)  
? Restricted web origins  
? Brute force protection enabled  
? Token lifespan limits  
? Session timeout configuration  

### Required for Production
? Change all client secrets  
? Disable test-client  
? Enable SSL/TLS  
? Use PostgreSQL database  
? Configure proper hostname  
? Implement secrets management  
? Enable comprehensive audit logging  

## Production Considerations

For production deployments, you should:

1. **Security:**
   - Change all client secrets to cryptographically secure values
   - Disable or remove `test-client`
   - Update redirect URIs to production domains
   - Enable SSL/TLS (`sslRequired: "external"`)
   - Use secrets management (Azure Key Vault, AWS Secrets Manager, HashiCorp Vault)

2. **Database:**
   - Use PostgreSQL instead of H2 database
   - Configure connection pooling
   - Enable database backups

3. **Configuration:**
   - Set strong admin passwords
   - Configure proper hostname settings
   - Enable strict hostname validation
   - Configure rate limiting and brute force protection
   - Set appropriate token lifespans

4. **Monitoring:**
   - Enable audit logging
   - Configure event listeners
   - Set up monitoring and alerting
   - Enable metrics collection

See [Security Guide](../../docs/security/security-guide.md) for detailed security configuration.

## Customizing the Realm

To modify the realm configuration:
1. Access the admin console at http://localhost:8180
2. Login with admin credentials
3. Make your changes in the UI
4. Export the realm: Realm Settings ? Action ? Partial Export
5. Replace `realm-export.json` with the exported configuration

**Note:** When exporting, include client secrets if needed, but never commit them to public repositories!

## Troubleshooting

### Container won't start
- Check if port 8180 is already in use
- Review logs: `docker-compose logs keycloak`

### Realm not imported
- Verify `realm-export.json` is valid JSON
- Check container logs for import errors
- Ensure the realm file is properly mounted

### Token validation fails
- Verify JWKS endpoint is accessible from gateway
- Check token expiration time
- Ensure correct realm and client configuration
- Verify client secret is correct (if using confidential client)

### Client authentication fails
**Error:** "Invalid client credentials"
**Solution:**
- Verify client secret is correct
- Check that `publicClient: false` for confidential clients
- Ensure `serviceAccountsEnabled: true` for client credentials flow

### Redirect URI mismatch
**Error:** "Invalid redirect_uri"
**Solution:**
- Verify redirect URI matches exactly (including trailing slashes)
- Check that the URI is in the allowed list
- Update `redirectUris` in client configuration

### Deprecation Warnings
If you see warnings about deprecated environment variables:
- Use `KC_BOOTSTRAP_ADMIN_USERNAME` instead of `KEYCLOAK_ADMIN`
- Use `KC_BOOTSTRAP_ADMIN_PASSWORD` instead of `KEYCLOAK_ADMIN_PASSWORD`
- Remove `KC_HOSTNAME_STRICT_HTTPS` (deprecated in favor of newer hostname options)

## References

- [Security Guide](../../docs/security/security-guide.md) - Complete security documentation
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [OpenID Connect Specification](https://openid.net/connect/)
