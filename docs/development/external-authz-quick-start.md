# External Authorization Quick Start

Quick reference for working with the external authorization service.

## Architecture Overview

```
Client → Envoy (JWT validation) → AuthZ Service (role lookup) → RBAC → Service
```

## Mock Users & Roles

| Email | Roles | Access Level |
|-------|-------|--------------|
| test.user-unvrfd@example.com | unverified-user | Very limited accees (Email not verified) |
| test.user-vrfd@example.com | verified-user | Limited access (Email verified, incomplete profile) |
| test.user@example.com | user | Basic access (profile completed) |
| test.user-cm@example.com | user, customer-manager | Can manage customers |
| test.user-pm@example.com | user, product-manager | Can manage products |
| test.user-pcm@example.com | user, product-category-manager | Can manage products in the category they are responsible for |
| admin.user@example.com | user, admin| System management |

## Common Commands

### Start Services
```powershell
docker-compose up -d --build
```

### Check AuthZ Service Health
```powershell
docker-compose ps authz-service
docker-compose logs -f authz-service
```

### Get Token and Access API
```powershell
# Get token
$response = Invoke-RestMethod -Uri "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token" `
  -Method POST -ContentType "application/x-www-form-urlencoded" `
  -Body @{client_id="test-client"; username="testuser"; password="testpass"; grant_type="password"}
$TOKEN = $response.access_token

# Access customers
Invoke-RestMethod -Uri "http://localhost:8080/customers" -Headers @{Authorization="Bearer $TOKEN"}

# Access products
Invoke-RestMethod -Uri "http://localhost:8080/products" -Headers @{Authorization="Bearer $TOKEN"}
```

### View AuthZ Logs
```powershell
# All logs
docker-compose logs authz-service

# Follow logs
docker-compose logs -f authz-service

# Filter by user
docker-compose logs authz-service | Select-String "testuser@example.com"

# Show only role lookups
docker-compose logs authz-service | Select-String "Roles found"
```

### Debug Issues
```powershell
# Check if services can communicate
docker-compose exec gateway ping authz-service

# Inspect authz service
docker-compose exec authz-service curl http://localhost:9000/authz/health

# Check Envoy configuration
docker-compose exec gateway cat /etc/envoy/envoy.yaml
```

## Testing Different Users

### Regular User (testuser)
```powershell
$TOKEN = (Invoke-RestMethod -Uri "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token" `
  -Method POST -ContentType "application/x-www-form-urlencoded" `
  -Body @{client_id="test-client"; username="testuser"; password="testpass"; grant_type="password"}).access_token
  
Invoke-RestMethod -Uri "http://localhost:8080/customers" -Headers @{Authorization="Bearer $TOKEN"}
# Expected: 200 OK, filtered customers
```

### Customer Manager (testuser-cm)
```powershell
# Note: Create testuser-cm user in Keycloak first
$TOKEN = (Invoke-RestMethod -Uri "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token" `
  -Method POST -ContentType "application/x-www-form-urlencoded" `
  -Body @{client_id="test-client"; username="testuser-cm"; password="testpass"; grant_type="password"}).access_token
  
Invoke-RestMethod -Uri "http://localhost:8080/customers" -Headers @{Authorization="Bearer $TOKEN"}
# Expected: 200 OK, all customers
```

## Adding New Users

### Step 1: Add to AuthZ Database
Edit `services/authz-service/authz_data_access.py`:
```python
USER_ROLES_DB = {
    "test.user@example.com": ["user"],
    "test.user-cm@example.com": ["user", "customer-manager"],
    # Add new user here
    "newuser@example.com": ["user"],
}
```

### Step 2: Rebuild AuthZ Service
```powershell
docker-compose up -d --build authz-service
```

### Step 3: Create User in Keycloak
1. Go to http://localhost:8180
2. Login as admin/admin
3. Create user with matching email
4. Set password

## Monitoring

### Check Request Flow
```powershell
# Terminal 1: Watch authz service
docker-compose logs -f authz-service

# Terminal 2: Make request
$TOKEN = (Invoke-RestMethod ...).access_token
Invoke-RestMethod -Uri "http://localhost:8080/customers" -Headers @{Authorization="Bearer $TOKEN"}

# Observe in Terminal 1:
# - JWT decoded
# - Email extracted
# - Roles retrieved
# - Response headers set
```

### Performance Monitoring
```powershell
# Check authz service response times in logs
docker-compose logs authz-service | Select-String "AuthZ role lookup"

# Monitor gateway logs for ext_authz calls
docker-compose logs gateway | Select-String "ext_authz"
```

## Troubleshooting

### "User not found in role database"
- Check if user email is in `USER_ROLES_DB`
- Email must match exactly (case-insensitive)
- Rebuild authz service after changes

### "Missing authorization header"
- Ensure token is included: `-Headers @{Authorization="Bearer $TOKEN"}`
- Check token is not expired (5 min default)

### AuthZ service not responding
```powershell
# Check health
docker-compose ps authz-service

# Restart service
docker-compose restart authz-service

# View startup logs
docker-compose logs authz-service
```

### Gateway can't reach authz service
```powershell
# Check network connectivity
docker-compose exec gateway ping authz-service

# Verify authz service is running
docker-compose ps authz-service

# Check depends_on in docker-compose.yml
```

## Integration Tests

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run external authz tests only
pytest tests/integration/test_external_authz.py -v

# Run all integration tests
pytest tests/integration/ -v

# Run with detailed output
pytest tests/integration/test_external_authz.py -v -s
```

## Phase B (Redis Caching) - Coming Soon

Future enhancements:
- Redis container for caching
- Cache TTL: 5 minutes
- Expected cache hit rate: 90-95%
- Latency reduction: ~10ms per cached request

See [Implementation Plan](external-authz-implementation-plan.md) for Phase B details.

## Related Documentation

- [Implementation Plan](external-authz-implementation-plan.md) - Comprehensive plan
- [Phase A Summary](phase-a-implementation-summary.md) - Implementation details
- [AuthZ Service README](../../services/authz-service/README.md) - Service documentation
- [System Architecture](../architecture/system-architecture.md) - Overall architecture

---

**Quick Help**: Having issues? Check logs first with `docker-compose logs -f authz-service`
