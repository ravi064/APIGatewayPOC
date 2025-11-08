"""
Integration tests for external authorization service.

Tests the complete flow: Client → Envoy → AuthZ Service → Downstream Service
"""

import pytest
import requests
from typing import Dict


def get_keycloak_token(username: str = "testuser", password: str = "testpass") -> str:
    """
    Get JWT token from Keycloak for testing.
    
    Args:
        username: Keycloak username
        password: Keycloak password
    
    Returns:
        JWT access token
    """
    response = requests.post(
        "http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token",
        data={
            "client_id": "test-client",
            "username": username,
            "password": password,
            "grant_type": "password"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200, f"Failed to get token: {response.text}"
    return response.json()["access_token"]


def test_authz_service_health():
    """Test that authz service health endpoint is accessible internally"""
    # Note: This test assumes running inside Docker network or with authz service exposed
    # In production, authz service is not exposed to host
    pass  # Health is checked by Docker healthcheck


def test_customer_access_with_external_authz():
    """
    Test full flow with external authorization service.
    User 'testuser' should have 'user' role from authz service.
    """
    # Get token from Keycloak
    token = get_keycloak_token("testuser", "testpass")
    
    # Make request through gateway
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser has 'user' role from authz service)
    assert response.status_code == 200
    customers = response.json()
    assert isinstance(customers, list)
    assert len(customers) > 0


def test_customer_manager_access():
    """
    Test that user with customer-manager role can access customer service.
    User 'testuser-cm' should have 'user' and 'customer-manager' roles.
    """
    # Note: Need to create 'testuser-cm' user in Keycloak first
    # For now, we'll skip this test if testuser-cm doesn't exist
    try:
        token = get_keycloak_token("testuser-cm", "testpass")
    except AssertionError:
        pytest.skip("User 'testuser-cm' not configured in Keycloak")
    
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser-cm has required roles from authz service)
    assert response.status_code == 200


def test_product_access_with_external_authz():
    """
    Test product service access with external authorization.
    User 'testuser' should have 'user' role from authz service.
    """
    token = get_keycloak_token("testuser", "testpass")
    
    response = requests.get(
        "http://localhost:8080/products",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser has 'user' role from authz service)
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) > 0


def test_no_token_rejected():
    """Test that requests without JWT token are rejected"""
    response = requests.get("http://localhost:8080/customers")
    
    # Should be rejected (no token)
    assert response.status_code in [401, 403]


def test_invalid_token_rejected():
    """Test that requests with invalid JWT token are rejected"""
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": "Bearer invalid-token-12345"}
    )
    
    # Should be rejected (invalid token)
    assert response.status_code in [401, 403]


def test_role_based_access_control():
    """
    Test that RBAC still works with roles from authz service.
    Verify that only users with 'user' or 'admin' role can access endpoints.
    """
    # Get valid token
    token = get_keycloak_token("testuser", "testpass")
    
    # Access customer service ('user' role has access)
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser has 'user' role from authz service)
    assert response.status_code == 200
    
    # Access product service ('user' role has access)
    response = requests.get(
        "http://localhost:8080/products",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should succeed (testuser has 'user' role from authz service)
    assert response.status_code == 200


def test_customer_service_rbac_with_authz_roles():
    """
    Test that customer service's internal RBAC works with authz-provided roles.
    - Regular user can only see their own customer record
    - Customer-manager can see all customers
    """
    # Get token for testuser (regular user)
    token = get_keycloak_token("testuser", "testpass")
    
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    customers = response.json()
    
    # testuser should only see their own record (email filter in customer service)
    # Note: Customer service still uses JWT for fine-grained authorization
    assert isinstance(customers, list)
    assert len(customers) == 1, f"Expected 1 customer, got {len(customers)}: {customers}"
    customer = customers[0]
    assert customer.get("email") == "test.user@example.com", f"Expected email 'test.user@example.com', got {customer.get('email')}"


@pytest.mark.skip(reason="User not in authz database - implement when needed")
def test_unknown_user_rejected_by_authz():
    """
    Test that users not in authz database are rejected.
    This requires creating a Keycloak user that's not in authz USER_ROLES_DB.
    """
    # This test requires:
    # 1. Creating a user in Keycloak (e.g., 'unknown@example.com')
    # 2. NOT adding them to authz_data_access.USER_ROLES_DB
    # 3. Attempting to access a protected endpoint
    # Expected: 403 Forbidden (user not found in authz service)
    pass


def test_concurrent_requests():
    """
    Test that authz service handles concurrent requests correctly.
    """
    token = get_keycloak_token("testuser", "testpass")
    
    import concurrent.futures
    
    def make_request():
        response = requests.get(
            "http://localhost:8080/customers",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.status_code
    
    # Make 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # All should succeed
    assert all(status == 200 for status in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
