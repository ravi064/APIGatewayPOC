"""
Integration tests for Product Service
"""
import pytest
import requests

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


class TestProductService:
    """Test product service endpoints"""
    
    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/products/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "product-service"
    
    def test_get_all_products_via_gateway(self):
        """Test getting all products through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(f"{GATEWAY_BASE_URL}/products", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) >= 3  # We have 3 mock products
     
        # Check first product structure
        product = products[0]
        assert "id" in product
        assert "name" in product
        assert "description" in product
        assert "price" in product
        assert "category" in product
        assert "stock_quantity" in product
        assert "created_at" in product
    
    def test_get_product_by_id_via_gateway(self):
        """Test getting specific product through API Gateway"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/products/1", headers=headers)
        assert response.status_code == 200
        product = response.json()
        assert product["id"] == 1
        assert product["name"] == "Laptop"
        assert product["category"] == "Electronics"
    
    def test_get_products_by_category(self):
        """Test getting products by category"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
    
        response = requests.get(f"{GATEWAY_BASE_URL}/products/category/Electronics", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) >= 2  # Laptop and Smartphone
        
        # All products should be in Electronics category
        for product in products:
            assert product["category"] == "Electronics"
    
    def test_get_products_by_nonexistent_category(self):
        """Test getting products by non-existent category"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/products/category/NonExistent", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) == 0
    
    def test_get_nonexistent_product(self):
        """Test getting non-existent product"""
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{GATEWAY_BASE_URL}/products/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Product not found" in error["detail"]
    
    def test_unauthorized_access_without_token(self):
        """Test that requests without token are rejected"""
        response = requests.get(f"{GATEWAY_BASE_URL}/products")
        assert response.status_code == 401  # Unauthorized
