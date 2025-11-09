# Product Service Test Objectives
#
# 1. Validate Product Service API Endpoints:
#    Ensure all product-related endpoints respond correctly to valid requests.
#
# 2. Verify Open Access Policy:
#    Confirm that all user roles (including guest/unauthenticated) can access product endpoints, as no RBAC restrictions are enforced.
#
# 3. Test Data Retrieval and Filtering:
#    Validate correct retrieval of all products, individual products by ID, and products by category, including handling of non-existent categories and products.
#
# 4. Check Health Check Endpoint:
#    Ensure the health check endpoint responds with correct service status.
#
# 5. Simulate Real-World User Scenarios:
#    Test access patterns for various user roles and unauthenticated (guest) users.
#
# 6. Error Handling and Edge Cases:
#    Ensure appropriate error responses for non-existent products and categories, and verify endpoint behavior for all access patterns.
#
"""
Integration tests for Product Service
"""
import pytest
import requests
# conftest.py functions and constants are automatically available
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import get_auth_headers, GATEWAY_BASE_URL



class TestProductService:
    """
    Test product service endpoints
    All roles (including unverified, verified, customer-manager, admin, product-manager, etc.)
    are allowed to access product information. No RBAC restrictions are enforced.
    """

    @pytest.mark.parametrize("username", [
        "testuser-unvrfd",
        "testuser-vrfd",
        "testuser",
        "testuser-cm",
        "adminuser",
        "testuser-pm",
    ])
    def test_get_all_products_via_gateway(self, username):
        """Test getting all products through API Gateway for all roles"""
        headers = get_auth_headers(username)
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

    @pytest.mark.parametrize("username", [
        "testuser-unvrfd",
        "testuser-vrfd",
        "testuser",
        "testuser-cm",
        "adminuser",
        "testuser-pm",
    ])
    def test_get_product_by_id_via_gateway(self, username):
        """Test getting specific product through API Gateway for all roles"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/products/1", headers=headers)
        assert response.status_code == 200
        product = response.json()
        assert product["id"] == 1
        assert product["name"] == "Laptop"
        assert product["category"] == "Electronics"

    @pytest.mark.parametrize("username", [
        "testuser-unvrfd",
        "testuser-vrfd",
        "testuser",
        "testuser-cm",
        "adminuser",
        "testuser-pm",
    ])
    def test_get_products_by_category(self, username):
        """Test getting products by category for all roles"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/products/category/Electronics", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) >= 2  # Laptop and Smartphone
        for product in products:
            assert product["category"] == "Electronics"

    @pytest.mark.parametrize("username", [
        "testuser-unvrfd",
        "testuser-vrfd",
        "testuser",
        "testuser-cm",
        "adminuser",
        "testuser-pm",
    ])
    def test_get_products_by_nonexistent_category(self, username):
        """Test getting products by non-existent category for all roles"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/products/category/NonExistent", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) == 0

    @pytest.mark.parametrize("username", [
        "testuser-unvrfd",
        "testuser-vrfd",
        "testuser",
        "testuser-cm",
        "adminuser",
        "testuser-pm",
    ])
    def test_get_nonexistent_product(self, username):
        """Test getting non-existent product for all roles"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/products/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Product not found" in error["detail"]

    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        headers = get_auth_headers("testuser")
        response = requests.get(f"{GATEWAY_BASE_URL}/products/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "product-service"

    @pytest.mark.parametrize("endpoint,expected_status,check", [
        ("/products", 200, "list"),
        ("/products/1", 200, "details"),
        ("/products/category/Electronics", 200, "category"),
        ("/products/category/NonExistent", 200, "empty"),
        ("/products/999", 404, "not_found"),
    ])
    def test_guest_access_without_token(self, endpoint, expected_status, check):
        """
        Parameterized test: unauthenticated (guest) users can access all product endpoints.
        No JWT token is provided; user is treated as 'guest'.
        """
        response = requests.get(f"{GATEWAY_BASE_URL}{endpoint}")
        assert response.status_code == expected_status
        data = response.json()
        if check == "list":
            assert isinstance(data, list)
            assert len(data) >= 3
        elif check == "details":
            assert data["id"] == 1
            assert data["name"] == "Laptop"
            assert data["category"] == "Electronics"
        elif check == "category":
            assert isinstance(data, list)
            assert len(data) >= 2
            for product in data:
                assert product["category"] == "Electronics"
        elif check == "empty":
            assert isinstance(data, list)
            assert len(data) == 0
        elif check == "not_found":
            assert "Product not found" in data["detail"]
