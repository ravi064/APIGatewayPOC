import requests
import pytest
import time

# Configuration
BASE_URL = "http://localhost:8080"
KEYCLOAK_BASE_URL = "http://localhost:8180"
KEYCLOAK_REALM = "api-gateway-poc"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

# Test credentials
TEST_CLIENT_ID = "test-client"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"


def get_access_token():
    """Get access token from Keycloak"""
    data = {
        "client_id": TEST_CLIENT_ID,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "grant_type": "password"
    }
    
    response = requests.post(
        KEYCLOAK_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        pytest.fail(f"Failed to get access token: {response.status_code} - {response.text}")
    
    token_data = response.json()
    return token_data["access_token"]


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for services to be ready before running tests"""
    max_retries = 10
    retry_count = 0
    
    # Wait for Keycloak first
    print("Waiting for Keycloak to be ready...")
    while retry_count < max_retries:
        try:
            response = requests.get(f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}", timeout=5)
            if response.status_code == 200:
                print("Keycloak is ready!")
                break
        except:
            pass
        
        retry_count += 1
        print(f"Waiting for Keycloak... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.fail("Keycloak did not start within the expected time")
    
    # Wait for Gateway and Services
    retry_count = 0
    print("Waiting for Gateway and Services to be ready...")
    while retry_count < max_retries:
        try:
            # Try to get a token and use it to check the services
            token = get_access_token()
            headers = {"Authorization": f"Bearer {token}"}

            # Check both customer and product services
            customer_response = requests.get(f"{BASE_URL}/customers/health", headers=headers, timeout=5)
            product_response = requests.get(f"{BASE_URL}/products/health", headers=headers, timeout=5)
            
            if customer_response.status_code == 200 and product_response.status_code == 200:
                print("Services are ready!")
                break
        except Exception as e:
            print(f"Service check failed: {e}")
        
        retry_count += 1
        print(f"Waiting for services... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.fail("Services did not start within the expected time")


def test_gateway_routing():
    """Test that the gateway routes requests correctly"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test customer service through gateway
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
    customers = response.json()
    assert isinstance(customers, list)
    assert len(customers) > 0
    
    # Test product service through gateway
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) > 0

def test_customer_service_health():
    """Test customer service health endpoint"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/customers/health", headers=headers)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "customer-service"

def test_product_service_health():
    """Test product service health endpoint"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/products/health", headers=headers)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "product-service"

def test_customer_by_id():
    """Test getting specific customer"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/customers/1", headers=headers)
    assert response.status_code == 200
    customer = response.json()
    assert customer["id"] == 1
    assert "name" in customer
    assert "email" in customer

def test_product_by_id():
    """Test getting specific product"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/products/1", headers=headers)
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == 1
    assert "name" in product
    assert "price" in product

def test_products_by_category():
    """Test getting products by category"""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/products/category/Electronics", headers=headers)
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    # Check that all returned products are in Electronics category
    for product in products:
        assert product["category"] == "Electronics"

def test_unauthorized_access_without_token():
    """Test that requests without token are rejected"""
    # Test customer service
    response = requests.get(f"{BASE_URL}/customers")
    assert response.status_code == 401  # Unauthorized

    # Test product service
    response = requests.get(f"{BASE_URL}/products")
    assert response.status_code == 401  # Unauthorized