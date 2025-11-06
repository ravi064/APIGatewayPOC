# Test Utilities Documentation

## Overview

The `tests/conftest.py` module provides centralized authentication utilities and fixtures for all integration tests. This eliminates code duplication and provides a consistent way to authenticate test users.

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
```
