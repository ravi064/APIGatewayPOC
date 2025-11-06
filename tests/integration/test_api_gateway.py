import requests
import pytest
import sys
import os

# Add parent directory to path to import conftest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import get_auth_headers, GATEWAY_BASE_URL

# Use gateway URL from conftest
BASE_URL = GATEWAY_BASE_URL


def test_gateway_routing():
    """Test that the gateway routes requests correctly"""
    headers = get_auth_headers("testuser-cm")
 
    # Test customer service through gateway
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
    customers = response.json()
    assert isinstance(customers, list)
    assert len(customers) > 0
    
    # Test product service through gateway
    headers = get_auth_headers("testuser-pm")
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) > 0


def test_customer_service_health():
    """Test customer service health endpoint"""
    headers = get_auth_headers("testuser")

    response = requests.get(f"{BASE_URL}/customers/health", headers=headers)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "customer-service"


def test_product_service_health():
    """Test product service health endpoint"""
    headers = get_auth_headers("testuser")
    
    response = requests.get(f"{BASE_URL}/products/health", headers=headers)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "product-service"


def test_customer_by_id():
    """Test getting specific customer"""
    headers = get_auth_headers("testuser-cm")
    
    response = requests.get(f"{BASE_URL}/customers/1", headers=headers)
    assert response.status_code == 200
    customer = response.json()
    assert customer["id"] == 1
    assert "name" in customer
    assert "email" in customer


def test_product_by_id():
    """Test getting specific product"""
    headers = get_auth_headers("testuser-pm")
    
    response = requests.get(f"{BASE_URL}/products/1", headers=headers)
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == 1
    assert "name" in product
    assert "price" in product


def test_products_by_category():
    """Test getting products by category"""
    headers = get_auth_headers("testuser-pm")
    
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


def test_rbac_unverified_user_access():
    """Test RBAC - unverified users should be blocked"""
    headers = get_auth_headers("testuser-unvrfd")
 
    # Both should fail with 403 Forbidden
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    assert response.status_code == 403
    
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 403


def test_rbac_verified_user_access():
    """Test RBAC - verified users should have access"""
    headers = get_auth_headers("testuser-cm")
    
    # Both should succeed
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
    
    headers = get_auth_headers("testuser-pm")
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 200
