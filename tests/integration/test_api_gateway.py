
# API Gateway Integration Test Objectives
#
# 1. Validate Gateway Routing:
#    Ensure requests to /customers and /products are correctly routed to their respective services.
#
# 2. Verify Role-Based Access Control (RBAC):
#    Confirm that the gateway enforces RBAC policies, allowing or denying access based on user roles as set by the authz-service.
#
# 3. Test Authentication Enforcement:
#    Ensure endpoints requiring JWT tokens (e.g., /customers) reject unauthenticated requests, while endpoints with open access (e.g., /products for guests) behave as expected.
#
# 4. Check Health Endpoints:
#    Validate that health endpoints for all services are accessible and return correct status. This includes /customers/health, /products/health, and /auth/health (for Keycloak).
#
# 5. Validate Data Integrity:
#    Confirm that data returned from services (lists, details, categories) is correct and matches expectations.
#
# 6. Test Error Handling:
#    Ensure the gateway and services return appropriate error codes (401, 403, 404) for unauthorized, forbidden, and not found scenarios.
#
# 7. End-to-End Security:
#    Simulate real-world access patterns through the gateway, verifying that only authorized users can access protected resources.
#
# Note: /auth/health endpoint (Keycloak health) is part of health checks and should be tested for availability and correct status.

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



@pytest.mark.parametrize("endpoint,role,expected_status", [
    ("/customers", "testuser-cm", 200),
    ("/products", "testuser-pm", 200),
])
def test_gateway_routing_and_access(endpoint, role, expected_status):
    """
    Test that the gateway routes requests correctly and enforces access for valid roles.
    """
    headers = get_auth_headers(role)
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    assert response.status_code == expected_status
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.parametrize("endpoint,expected_service,role", [
    ("/customers/health", "customer-service", "testuser"),
    ("/products/health", "product-service", None),
])
def test_gateway_health_endpoints(endpoint, expected_service, role):
    """
    Parameterized test for health endpoints through gateway.
    Verifies status code and service name in response.
    Adds JWT token for customer service health check.
    """
    headers = get_auth_headers(role) if role else None
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == expected_service


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




@pytest.mark.parametrize("endpoint,expected_status", [
    ("/customers", 401),
    ("/products", 200),
])
def test_unauthorized_access_without_token(endpoint, expected_status):
    """
    Test that requests without token are rejected by gateway for protected endpoints, and allowed for open endpoints.
    """
    response = requests.get(f"{BASE_URL}{endpoint}")
    assert response.status_code == expected_status



def test_rbac_unverified_user_access():
    """
    Test RBAC: unverified users should be allowed for customers, and products.
    """
    headers = get_auth_headers("testuser-unvrfd")
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 200



@pytest.mark.parametrize("endpoint,role", [
    ("/customers", "testuser-cm"),
    ("/products", "testuser-pm"),
])
def test_rbac_verified_user_access(endpoint, role):
    """
    Test RBAC: verified users should have access to their respective endpoints.
    """
    headers = get_auth_headers(role)
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    assert response.status_code == 200
