"""
Shared test fixtures and utilities for integration tests
"""
import requests
import pytest
import time
from typing import Dict, Optional

# Configuration
GATEWAY_BASE_URL = "http://localhost:8080"
KEYCLOAK_BASE_URL = "http://localhost:8180"
KEYCLOAK_REALM = "api-gateway-poc"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
TEST_CLIENT_ID = "test-client"

# Test user credentials
TEST_USERS = {
    "testuser-unvrfd": {"username": "testuser-unvrfd", "password": "testpass", "roles": ["unverified-user"]},
    "testuser-vrfd": {"username": "testuser-vrfd", "password": "testpass", "roles": ["verified-user"]},
    "testuser": {"username": "testuser", "password": "testpass", "roles": ["user"]},
    "adminuser": {"username": "adminuser", "password": "adminpass", "roles": ["user", "admin"]},
    "testuser-cm": {"username": "testuser-cm", "password": "testpass", "roles": ["user", "customer-manager"]},
    "testuser-pm": {"username": "testuser-pm", "password": "testpass", "roles": ["user", "product-manager"]},
    "testuser-pcm": {"username": "testuser-pcm", "password": "testpass", "roles": ["user", "product-category-manager"]},
}


def get_access_token(username: str = "testuser", password: Optional[str] = None) -> str:
    """
    Get access token from Keycloak for a specified user.
    
    Args:
        username: Username to authenticate (default: "testuser")
        password: Password for the user (optional, will use predefined password if not provided)
    
    Returns:
        str: JWT access token
    
    Raises:
        pytest.fail: If token retrieval fails
    
    Examples:
        >>> token = get_access_token()  # Default testuser
        >>> token = get_access_token("adminuser")
        >>> token = get_access_token("testuser-unvrfd", "custompass")
    """
    # Get password from TEST_USERS if not provided
    if password is None:
        if username in TEST_USERS:
            password = TEST_USERS[username]["password"]
        else:
            pytest.fail(f"Unknown user '{username}'. Available users: {list(TEST_USERS.keys())}")
    
    data = {
        "client_id": TEST_CLIENT_ID,
        "username": username,
        "password": password,
        "grant_type": "password"
    }
    
    response = requests.post(
        KEYCLOAK_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        pytest.fail(
            f"Failed to get access token for user '{username}': "
            f"{response.status_code} - {response.text}"
        )
    
    token_data = response.json()
    return token_data["access_token"]


def get_auth_headers(username: str = "testuser") -> Dict[str, str]:
    """
    Get authorization headers with Bearer token for a specified user.
    
    Args:
        username: Username to authenticate (default: "testuser")
    
    Returns:
        Dict[str, str]: Headers dictionary with Authorization header
    
    Examples:
        >>> headers = get_auth_headers()
        >>> headers = get_auth_headers("adminuser")
        >>> response = requests.get(url, headers=headers)
    """
    token = get_access_token(username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def keycloak_url():
    """Keycloak base URL fixture"""
    return KEYCLOAK_BASE_URL


@pytest.fixture(scope="session")
def gateway_url():
    """API Gateway base URL fixture"""
    return GATEWAY_BASE_URL


@pytest.fixture(scope="session")
def test_users():
    """Test users dictionary fixture"""
    return TEST_USERS


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for services to be ready before running tests"""
    max_retries = 10
    retry_count = 0
    
    # Wait for Keycloak first
    print("\n" + "="*60)
    print("Waiting for Keycloak to be ready...")
    print("="*60)
    while retry_count < max_retries:
        try:
            response = requests.get(f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}", timeout=5)
            if response.status_code == 200:
                print("[OK] Keycloak is ready!")
                break
        except:
            pass
        
        retry_count += 1
        print(f"[WAIT] Waiting for Keycloak... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.fail("[ERROR] Keycloak did not start within the expected time")
    
    # Wait for Gateway and Services
    retry_count = 0
    print("\n" + "="*60)
    print("Waiting for Gateway and Services to be ready...")
    print("="*60)
    while retry_count < max_retries:
        try:
            # Try to get a token and use it to check the services
            token = get_access_token("testuser")
            headers = {"Authorization": f"Bearer {token}"}

            # Check both customer and product services
            customer_response = requests.get(
                f"{GATEWAY_BASE_URL}/customers/health", 
                headers=headers, 
                timeout=5
            )
            product_response = requests.get(
                f"{GATEWAY_BASE_URL}/products/health", 
                headers=headers, 
                timeout=5
            )
            
            if customer_response.status_code == 200 and product_response.status_code == 200:
                print("[OK] All services are ready!")
                print("="*60 + "\n")
                break
        except Exception as e:
            print(f"[WAIT] Service check failed: {e}")
        
        retry_count += 1
        print(f"[WAIT] Waiting for services... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.fail("[ERROR] Services did not start within the expected time")


@pytest.fixture
def unverified_user_token():
    """Fixture for unverified user token"""
    return get_access_token("testuser-unvrfd")


@pytest.fixture
def verified_user_token():
    """Fixture for verified user token"""
    return get_access_token("testuser-vrfd")


@pytest.fixture
def admin_user_token():
    """Fixture for admin user token"""
    return get_access_token("adminuser")


@pytest.fixture
def customer_manager_token():
    """Fixture for customer manager token"""
    return get_access_token("testuser-cm")


@pytest.fixture
def product_manager_token():
    """Fixture for product manager token"""
    return get_access_token("testuser-pm")


@pytest.fixture
def product_category_manager_token():
    """Fixture for product category manager token"""
    return get_access_token("testuser-pcm")