# Customer Service Test Objectives
#
# 1. Validate Customer Service API Endpoints:
#    Ensure all customer-related endpoints respond correctly to valid requests.
#
# 2. Verify RBAC Enforcement:
#    Confirm that access to customer data is restricted based on user roles (e.g., regular user, customer manager, admin).
#
# 3. Test JWT Authentication:
#    Ensure endpoints require valid JWT tokens and reject requests with missing or invalid tokens.
#
# 4. Check Data Integrity and Validation:
#    Validate that customer data is correctly created, retrieved, updated, and deleted, and that input validation is enforced.
#
# 5. Simulate Real-World User Scenarios:
#    Test access patterns for different user roles, including edge cases (unknown user, guest, etc.).
#
# 6. Error Handling and Edge Cases:
#    Ensure appropriate error responses for invalid input, unauthorized access, and unexpected conditions.
#

"""
Integration tests for Customer Service (revised for new RBAC logic)
"""
import pytest
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import get_auth_headers, GATEWAY_BASE_URL


class TestCustomerService:
    """Test customer service endpoints and RBAC logic"""

    @pytest.mark.parametrize("username,expected_status", [
        ("testuser-unvrfd", 200),
        ("testuser-vrfd", 200),
        ("testuser", 200),
        ("testuser-cm", 200),
        ("adminuser", 200),
        ("testuser-pm", 200),
    ])
    def test_customers_list_access(self, username, expected_status):
        """Test /customers endpoint for various roles"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == expected_status
        if expected_status == 200:
            customers = response.json()
            assert isinstance(customers, list)
            # For guest, should not reach here
            if username == "testuser-cm":
                assert len(customers) >= 7
            else:
                assert len(customers) == 1

    @pytest.mark.parametrize("username,customer_id,expected_status", [
        ("testuser-unvrfd", 1, 200),
        ("testuser-vrfd", 2, 200),
        ("testuser", 3, 200),
        ("testuser-cm", 3, 200),
        ("adminuser", 7, 200),
        ("testuser-pm", 5, 200),
        ("testuser", 7, 403),
        ("adminuser", 2, 403),
        ("testuser-pm", 2, 403),
    ])
    def test_customer_by_id_access(self, username, customer_id, expected_status):
        """Test /customers/{customer_id} endpoint for various roles and IDs"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/{customer_id}", headers=headers)
        assert response.status_code == expected_status
        if expected_status == 200:
            customer = response.json()
            assert customer["id"] == customer_id
            assert "email" in customer

    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        headers = get_auth_headers("testuser")
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "customer-service"

    def test_unauthorized_access_without_token(self):
        """Test that requests without token are rejected"""
        response = requests.get(f"{GATEWAY_BASE_URL}/customers")
        assert response.status_code == 401

    @pytest.mark.parametrize("username,customer_id", [
        ("testuser-unvrfd", 999),
        ("testuser-vrfd", 999),
        ("testuser", 999),
        ("adminuser", 999),
        ("testuser-pm", 999),
    ])
    def test_nonexistent_customer_access(self, username, customer_id):
        """Test that all roles except customer-manager get 403 for non-existent customer"""
        headers = get_auth_headers(username)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/{customer_id}", headers=headers)
        assert response.status_code == 403
        error = response.json()
        assert "Access denied" in error["detail"]

    def test_customer_manager_access_nonexistent_customer(self):
        """Test that customer-manager gets 404 for non-existent customer"""
        headers = get_auth_headers("testuser-cm")
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Customer not found" in error["detail"]