"""
Integration tests for Customer Service
"""
import pytest
import requests
import time

# Configuration
GATEWAY_BASE_URL = "http://localhost:8080"
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


class TestCustomerService:
    """Test customer service endpoints"""
    
    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "customer-service"
    
    def test_get_all_customers_via_gateway(self):
        """Test getting all customers through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert isinstance(customers, list)
        assert len(customers) >= 7  # We have 7 mock customers
        
        # Check first customer structure
        customer = customers[0]
        assert "id" in customer
        assert "name" in customer
        assert "email" in customer
        assert "created_at" in customer
    
    def test_get_customer_by_id_via_gateway(self):
        """Test getting specific customer through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/6", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 6
        assert customer["name"] == "John Doe"
        assert customer["email"] == "john.doe@example.com"
    
    def test_get_nonexistent_customer(self):
        """Test getting non-existent customer"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Customer not found" in error["detail"]
    
    def test_unauthorized_access_without_token(self):
        """Test that requests without token are rejected"""
        response = requests.get(f"{GATEWAY_BASE_URL}/customers")
        assert response.status_code == 401  # Unauthorized


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for services to be ready before running tests"""
    import time
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
    
    # Wait for Gateway and Customer Service
    retry_count = 0
    print("Waiting for Gateway and Customer Service to be ready...")
    while retry_count < max_retries:
        try:
            # Try to get a token and use it to check the service
            token = get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{GATEWAY_BASE_URL}/customers/health", headers=headers, timeout=5)
            if response.status_code == 200:
                print("Services are ready!")
                break
        except Exception as e:
            print(f"Service check failed: {e}")
        
        retry_count += 1
        print(f"Waiting for services... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    if retry_count >= max_retries:
        pytest.fail("Services did not start within the expected time")