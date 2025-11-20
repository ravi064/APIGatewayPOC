# Test Utilities Documentation

## Overview

The `tests/conftest.py` module provides centralized authentication utilities and fixtures for all integration tests. This eliminates code duplication and provides a consistent way to authenticate test users.

---

## JWT Security Tests

### Overview

The project includes comprehensive JWT security tests that validate the API gateway's defense against common JWT-based attacks. These tests ensure that signature verification, expiration enforcement, and issuer validation are properly configured.

**Location:** `tests/integration/test_api_gateway.py`

**Why These Tests Matter:**
- Prove that JWT signature verification is enforced
- Validate defense against token tampering attacks
- Ensure expired tokens are rejected
- Verify only trusted identity providers are accepted

---

### Test 1: JWT Tampering Detection (`test_jwt_tampering_rejected`)

**Purpose:** Verify that tampering with JWT claims is detected and rejected.

**Attack Scenario:**
1. User authenticates as `testuser` (test.user@example.com)
2. Attacker intercepts the JWT token
3. Attacker modifies the `email` claim to `test.user-cm@example.com` to impersonate a privileged user
4. Attacker sends the tampered token to access `/customers` endpoint

**Expected Behavior:**
- Gateway rejects the request with `401 Unauthorized`
- Response body: `"Jwt verification fails"`
- Response header: `server: envoy` (proves rejection at gateway)

**What It Validates:**
- ? JWT signature verification is enforced at Envoy gateway
- ? Users cannot escalate privileges by modifying JWT claims
- ? Defense-in-depth: Attack blocked before reaching backend services

**How to Run:**
```bash
pytest tests/integration/test_api_gateway.py::test_jwt_tampering_rejected -v -s
```

**Expected Output:**
```
======================================================================
JWT TAMPERING SECURITY TEST RESULTS
======================================================================
Original email:    test.user@example.com
Tampered email:    test.user-cm@example.com
Response status:   401
Response headers:  {'server': 'envoy', 'www-authenticate': 'Bearer realm="..."', ...}
Response body:     Jwt verification fails
======================================================================

? Security test passed: Tampered JWT rejected with status 401
PASSED
```

---

### Test 2: Expired Token Detection (`test_jwt_expired_token_rejected`)

**Purpose:** Verify that expired JWT tokens are rejected.

**Attack Scenario:**
1. User authenticates and gets a valid JWT token
2. Attacker modifies the `exp` (expiration) claim to extend the token's lifetime
3. Attacker attempts to use the modified token to access `/customers` endpoint

**Expected Behavior:**
- Gateway rejects the request with `401 Unauthorized`
- Signature validation fails because `exp` claim was modified

**What It Validates:**
- ? Token expiration cannot be bypassed by modifying `exp` claim
- ? Signature verification prevents tampering with expiration time
- ? Old/stolen tokens cannot be reused beyond their lifetime

**How to Run:**
```bash
pytest tests/integration/test_api_gateway.py::test_jwt_expired_token_rejected -v -s
```

**Expected Output:**
```
======================================================================
JWT EXPIRATION SECURITY TEST RESULTS
======================================================================
Original exp:      1732003694
Tampered exp:      1731996494 (1 hour ago)
Response status:   401
Response body:     Jwt verification fails
======================================================================

? Security test passed: Expired JWT rejected with status 401
PASSED
```

---

### Test 3: Issuer Validation (`test_jwt_wrong_issuer_rejected`)

**Purpose:** Verify that JWT tokens from untrusted issuers are rejected.

**Attack Scenario:**
1. Attacker sets up a fake Keycloak instance
2. Attacker modifies the `iss` (issuer) claim in a legitimate token
3. Attacker attempts to use the token with modified issuer to access `/customers` endpoint

**Expected Behavior:**
- Gateway rejects the request with `401 Unauthorized`
- Signature validation fails because `iss` claim was modified

**What It Validates:**
- ? Only tokens from trusted Keycloak instance are accepted
- ? Tokens from malicious identity providers are rejected
- ? Issuer validation prevents token source spoofing

**How to Run:**
```bash
pytest tests/integration/test_api_gateway.py::test_jwt_wrong_issuer_rejected -v -s
```

**Expected Output:**
```
======================================================================
JWT ISSUER SECURITY TEST RESULTS
======================================================================
Original issuer:   http://localhost:8180/realms/api-gateway-poc
Tampered issuer:   http://malicious-keycloak.example.com/realms/fake-realm
Response status:   401
Response body:     Jwt verification fails
======================================================================

? Security test passed: JWT with wrong issuer rejected with status 401
PASSED
```

---

### Running All JWT Security Tests

**Run all JWT security tests together:**
```bash
pytest tests/integration/test_api_gateway.py -k "jwt" -v -s
```

**Expected Output (All Pass):**
```
tests/integration/test_api_gateway.py::test_jwt_tampering_rejected PASSED
tests/integration/test_api_gateway.py::test_jwt_expired_token_rejected PASSED
tests/integration/test_api_gateway.py::test_jwt_wrong_issuer_rejected PASSED

============================== 3 passed in 0.45s ==============================
```

---

### How JWT Tampering Tests Work

All three tests follow the same pattern:

1. **Get Legitimate Token:**
   ```python
   token = get_access_token("testuser")
   ```

2. **Decode JWT Payload:**
   ```python
   # JWT structure: header.payload.signature
   parts = token.split('.')
   payload = base64_decode(parts[1])
   ```

3. **Modify a Claim:**
   ```python
   payload["email"] = "test.user-cm@example.com"  # Tampering
   ```

4. **Re-encode with Original Signature:**
   ```python
   tampered_token = f"{parts[0]}.{new_payload}.{parts[2]}"
   # Signature is now invalid for the modified payload
   ```

5. **Attempt Request:**
   ```python
   response = requests.get("/customers", headers={"Authorization": f"Bearer {tampered_token}"})
   ```

6. **Verify Rejection:**
   ```python
   assert response.status_code == 401
   ```

**Why It Works:**
- JWT signatures are computed over the entire payload
- Modifying any claim invalidates the signature
- Envoy validates the signature and rejects mismatches
- Attack is blocked at the gateway (defense in depth)

---

### Security Test Results Analysis

**What Successful Tests Prove:**
- ? **Envoy JWT filter is properly configured** - Validates signatures before forwarding
- ? **Signature verification is enforced** - Modified payloads are rejected
- ? **Defense in depth** - Attacks blocked at gateway, not backend
- ? **No privilege escalation** - Users cannot impersonate other users
- ? **Token integrity** - Tampering is detected and rejected

**What Would Indicate a Security Issue:**
- ? Test returns `200 OK` - Token tampering succeeded (CRITICAL VULNERABILITY)
- ? Response contains data - Backend processed tampered token (SEVERE)
- ? `server: customer-service` header - Gateway didn't validate (MISCONFIGURATION)

---

### Debugging Failed Security Tests

If a JWT security test fails:

1. **Check Envoy JWT Filter Configuration:**
   ```yaml
   # In envoy.yaml
   jwt_authn:
     providers:
       keycloak:
         issuer: "http://localhost:8180/realms/api-gateway-poc"
         remote_jwks:
           http_uri:
             uri: "http://keycloak:8080/realms/api-gateway-poc/protocol/openid-connect/certs"
   ```

2. **Verify Signature Validation is Enabled:**
   ```yaml
   # Should NOT have this flag (disables verification):
   forward_payload_header: true  # Only use for testing!
   ```

3. **Check Envoy Logs:**
   ```bash
   docker logs envoy-proxy | grep "JWT"
   ```

4. **Test Token Manually:**
   ```bash
   # Get token
   TOKEN=$(curl -s -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
     -d "client_id=test-client&username=testuser&password=testpass&grant_type=password" \
     | jq -r '.access_token')
   
   # Test with valid token
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
   
   # Test with tampered token (should fail)
   curl -H "Authorization: Bearer invalid-token" http://localhost:8080/customers
   ```

---

### Adding New Security Tests

To add a new JWT security test:

1. **Follow the existing pattern:**
   ```python
   def test_jwt_[attack_type]_rejected():
       """Security test: Verify [attack] is rejected."""
       token = get_access_token("testuser")
       # Decode and modify JWT
       # Attempt request with tampered token
       # Assert rejection with 401
   ```

2. **Add to security documentation:**
   - Update `docs/security/security-guide.md`
   - Document the attack scenario
   - Explain what's validated

3. **Run the test:**
   ```bash
   pytest tests/integration/test_api_gateway.py::test_jwt_[attack_type]_rejected -v -s
   ```

**For security implications and defense architecture, see:** [Security Guide](../security/security-guide.md#jwt-security-validation)

---

## Available Test Users

All test users are defined in the `TEST_USERS` dictionary:

| Username | Password | Roles |
|----------|----------|-------|
| `testuser-unvrfd` | `testpass` | `unverified-user` |
| `testuser-vrfd` | `testpass` | `verified-user` |
| `testuser` | `testpass` | `user` |
| `adminuser` | `adminpass` | `user`, `admin` |
| `testuser-cm` | `testpass` | `user`, `customer-manager` |
| `testuser-pm` | `testpass` | `user`, `product-manager` |
| `testuser-pcm` | `testpass` | `user`, `product-category-manager` |

## Core Functions

### `get_access_token(username, password=None)`

Gets a JWT access token from Keycloak for the specified user.

**Parameters:**
- `username` (str): Username to authenticate (default: "testuser")
- `password` (str, optional): Password for the user (uses predefined password if not provided)

**Returns:**
- `str`: JWT access token

**Examples:**

```python
# Get token for default user (testuser)
token = get_access_token()

# Get token for specific user
token = get_access_token("adminuser")

# Get token with explicit password
token = get_access_token("customuser", "custompass")
```

**Raises:**
- `pytest.fail`: If token retrieval fails or unknown user

---

### `get_auth_headers(username)`

Gets authorization headers with Bearer token for the specified user.

**Parameters:**
- `username` (str): Username to authenticate (default: "testuser")

**Returns:**
- `Dict[str, str]`: Headers dictionary with Authorization header

**Examples:**

```python
# Get headers for default user
headers = get_auth_headers()

# Get headers for admin user
headers = get_auth_headers("adminuser")

# Use in requests
response = requests.get(url, headers=get_auth_headers("testuser"))
```

---

## Pytest Fixtures

### Session-Scoped Fixtures

These fixtures are created once per test session:

#### `wait_for_services` (autouse=True)
Automatically waits for Keycloak and services to be ready before running any tests.

#### `keycloak_url`
Provides Keycloak base URL.

```python
def test_example(keycloak_url):
    assert keycloak_url == "http://localhost:8180"
```

#### `gateway_url`
Provides API Gateway base URL.

```python
def test_example(gateway_url):
    response = requests.get(f"{gateway_url}/customers")
```

#### `test_users`
Provides the TEST_USERS dictionary.

```python
def test_example(test_users):
    assert "testuser" in test_users
    assert test_users["adminuser"]["password"] == "adminpass"
```

### Function-Scoped Token Fixtures

Get fresh tokens for each test (useful for isolation):

#### `unverified_user_token`
```python
def test_example(unverified_user_token):
    headers = {"Authorization": f"Bearer {unverified_user_token}"}
    response = requests.get(url, headers=headers)
```

#### `verified_user_token`
```python
def test_example(verified_user_token):
  headers = {"Authorization": f"Bearer {verified_user_token}"}
```

#### `admin_user_token`
```python
def test_example(admin_user_token):
    headers = {"Authorization": f"Bearer {admin_user_token}"}
```

#### `customer_manager_token`
```python
def test_example(customer_manager_token):
    headers = {"Authorization": f"Bearer {customer_manager_token}"}
```

#### `product_manager_token`
```python
def test_example(product_manager_token):
  headers = {"Authorization": f"Bearer {product_manager_token}"}
```

#### `product_category_manager_token`
```python
def test_example(product_category_manager_token):
    headers = {"Authorization": f"Bearer {product_category_manager_token}"}
```

---

## Usage Examples

### Simple Test with Default User

```python
from conftest import get_auth_headers, GATEWAY_BASE_URL
import requests

def test_get_customers():
    """Test getting customers with default user"""
    headers = get_auth_headers()  # Uses 'testuser' by default
    response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
```

### Test with Specific User

```python
from conftest import get_auth_headers, GATEWAY_BASE_URL
import requests

def test_admin_access():
    """Test admin user has full access"""
    headers = get_auth_headers("adminuser")
    response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
```

### Test RBAC Denial

```python
from conftest import get_auth_headers, GATEWAY_BASE_URL
import requests

def test_unverified_user_blocked():
    """Test unverified users are blocked"""
    headers = get_auth_headers("testuser-unvrfd")
    response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
    assert response.status_code == 403  # RBAC blocks unverified users
```

### Using Fixtures

```python
import requests

def test_with_fixture(admin_user_token, gateway_url):
    """Test using pytest fixtures"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = requests.get(f"{gateway_url}/customers", headers=headers)
    assert response.status_code == 200
```

### Testing Multiple Users

```python
from conftest import get_auth_headers, GATEWAY_BASE_URL, TEST_USERS
import requests
import pytest

@pytest.mark.parametrize("username", ["testuser", "adminuser", "testuser-cm"])
def test_verified_users_have_access(username):
    """Test that all verified users can access services"""
    headers = get_auth_headers(username)
    response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
```

---

## Configuration

All configuration is centralized in `conftest.py`:

```python
GATEWAY_BASE_URL = "http://localhost:8080"
KEYCLOAK_BASE_URL = "http://localhost:8180"
KEYCLOAK_REALM = "api-gateway-poc"
TEST_CLIENT_ID = "test-client"
```

Import these constants in your tests:

```python
from conftest import GATEWAY_BASE_URL, KEYCLOAK_BASE_URL
```

---

## Benefits

1. **DRY Principle**: No code duplication across test files
2. **Centralized User Management**: All test users defined in one place
3. **Consistent Authentication**: Same authentication logic everywhere
4. **Easy to Extend**: Add new users by updating TEST_USERS dictionary
5. **Better Readability**: Tests focus on business logic, not authentication
6. **Pytest Integration**: Leverages pytest fixtures for better test isolation

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_customer_service.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_customer_service.py::TestCustomerService::test_health_check_via_gateway

# Run tests matching pattern
pytest -k "rbac"
```

---

## Adding New Test Users

To add a new test user:

1. Add the user to `realm-export.json` in Keycloak configuration
2. Update `TEST_USERS` dictionary in `conftest.py`:

```python
TEST_USERS = {
    # ... existing users ...
    "newuser": {
        "username": "newuser",
        "password": "newpass",
        "roles": ["user", "custom-role"]
    },
}
```

3. Optionally add a fixture for convenience:

```python
@pytest.fixture
def new_user_token():
    """Fixture for new user token"""
    return get_access_token("newuser")
```

4. Use in tests:

```python
headers = get_auth_headers("newuser")
# or
def test_example(new_user_token):
    headers = {"Authorization": f"Bearer {new_user_token}"}
