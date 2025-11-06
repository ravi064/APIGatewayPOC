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
    """Test product service endpoints"""
    
    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        headers = get_auth_headers("testuser")
     
        response = requests.get(f"{GATEWAY_BASE_URL}/products/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "product-service"
  
    def test_get_all_products_via_gateway(self):
        """Test getting all products through API Gateway"""
        headers = get_auth_headers("testuser")

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
        headers = get_auth_headers("testuser")
    
        response = requests.get(f"{GATEWAY_BASE_URL}/products/1", headers=headers)
        assert response.status_code == 200
        product = response.json()
        assert product["id"] == 1
        assert product["name"] == "Laptop"
        assert product["category"] == "Electronics"
  
    def test_get_products_by_category(self):
        """Test getting products by category"""
        headers = get_auth_headers("testuser")
    
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
        headers = get_auth_headers("testuser")
    
        response = requests.get(f"{GATEWAY_BASE_URL}/products/category/NonExistent", headers=headers)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)
        assert len(products) == 0
    
    def test_get_nonexistent_product(self):
        """Test getting non-existent product"""
        headers = get_auth_headers("testuser")
        
        response = requests.get(f"{GATEWAY_BASE_URL}/products/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Product not found" in error["detail"]
    
    def test_unauthorized_access_without_token(self):
        """Test that requests without token are rejected"""
        response = requests.get(f"{GATEWAY_BASE_URL}/products")
        assert response.status_code == 401  # Unauthorized

    def test_unverified_user_blocked_from_products(self):
        """Test that unverified users cannot access product service"""
        headers = get_auth_headers("testuser-unvrfd")
    
        # Should get 403 Forbidden (RBAC blocks unverified users)
        response = requests.get(f"{GATEWAY_BASE_URL}/products", headers=headers)
        assert response.status_code == 403  # RBAC denial

    def test_verified_user_blocked_from_products(self):
        """Test that verified users cannot access product service"""
        headers = get_auth_headers("testuser-vrfd")
    
        # Should get 403 Forbidden (RBAC blocks verified users)
        response = requests.get(f"{GATEWAY_BASE_URL}/products", headers=headers)
        assert response.status_code == 403  # RBAC denial
