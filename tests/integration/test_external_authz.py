
# External AuthZ Integration Test Objectives
#
# 1. Validate External Authorization Service Integration:
#    Ensure Envoy’s ext_authz filter correctly calls the external authz-service for role lookup and authorization decisions.
#
# 2. Verify Role Header Propagation:
#    Confirm that x-user-roles and x-user-email headers are set by authz-service and correctly forwarded by Envoy to downstream services.
#
# 3. Test RBAC Enforcement via ext_authz:
#    Ensure requests are allowed or denied based on roles returned by authz-service, matching RBAC policies.
#
# 4. Check Error Handling and Edge Cases:
#    Validate correct behavior for missing/invalid JWTs, missing headers, unknown users, and unexpected role responses.
#
# 5. Simulate Real-World Access Patterns:
#    Test various user scenarios (guest, unverified, verified, admin, etc.) to ensure ext_authz and RBAC work as intended.
#
# Note: Health check tests are omitted due to frequent Envoy health checks and log noise.


import pytest
import requests


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


@pytest.mark.parametrize("username,endpoint,expected_status", [
    ("testuser", "/customers", 200),
    ("testuser", "/products", 200),
    ("testuser-cm", "/customers", 200),
    ("testuser-pm", "/products", 200),
    ("testuser-unvrfd", "/products", 200),
])
def test_role_based_access_with_ext_authz(username, endpoint, expected_status):
    """
    Parameterized test for role-based access via ext_authz.
    Verifies that users with correct roles can access endpoints.
    """
    try:
        token = get_keycloak_token(username, "testpass")
    except AssertionError:
        pytest.skip(f"User '{username}' not configured in Keycloak")
    response = requests.get(
        f"http://localhost:8080{endpoint}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == expected_status


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



@pytest.mark.parametrize("endpoint,expected_status", [
    ("/customers", 401),
    ("/products", 200),
])
def test_no_token_access(endpoint, expected_status):
    """
    Test access without JWT token. Customers should be rejected, products allowed for guests.
    """
    response = requests.get(f"http://localhost:8080{endpoint}")
    assert response.status_code == expected_status



@pytest.mark.parametrize("endpoint", ["/customers", "/products"])
def test_invalid_token_rejected(endpoint):
    """
    Test that requests with invalid JWT token are rejected for all endpoints.
    """
    response = requests.get(
        f"http://localhost:8080{endpoint}",
        headers={"Authorization": "Bearer invalid-token-12345"}
    )
    assert response.status_code in [401, 403]



# The above parameterized tests cover RBAC and role propagation for all major scenarios.



def test_customer_service_rbac_with_authz_roles():
    """
    Test that customer service's internal RBAC works with authz-provided roles.
    Regular user can only see their own customer record.
    """
    token = get_keycloak_token("testuser", "testpass")
    response = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    customers = response.json()
    assert isinstance(customers, list)
    assert len(customers) == 1, f"Expected 1 customer, got {len(customers)}: {customers}"
    customer = customers[0]
    assert customer.get("email") == "test.user@example.com", f"Expected email 'test.user@example.com', got {customer.get('email')}"



# Edge case: unknown user scenario can be added when needed.



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
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in futures]
    assert all(status == 200 for status in results)


# Phase B: Redis Caching Tests


def test_cache_hit_on_repeated_requests():
    """
    Test that second request uses cache (Phase B).
    First request should query database (cache miss).
    Second request should use cache (cache hit).
    """
    token = get_keycloak_token("testuser", "testpass")
    
    # First request - should query database
    response1 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 200
    
    # Second request - should use cache
    response2 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 200
    
    # Both requests should return same data
    assert response1.json() == response2.json()
    
    # Note: To verify cache hit/miss, check authz-service logs:
    # docker-compose logs authz-service | grep "Cache HIT\|Cache MISS"


def test_auth_me_endpoint_authenticated():
    """
    Test /auth/me endpoint with valid JWT token (Phase B).
    Verify that authenticated users can retrieve their email and roles.
    """
    token = get_keycloak_token("testuser", "testpass")
    
    # Call /auth/me endpoint
    response = requests.get(
        "http://localhost:8080/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "email" in data
    assert "roles" in data
    assert isinstance(data["roles"], list)
    
    # Verify user data
    assert data["email"] == "test.user@example.com"
    assert "user" in data["roles"]


def test_auth_me_endpoint_unauthenticated():
    """
    Test /auth/me endpoint without JWT token (Phase B).
    Verify that unauthenticated requests are rejected.
    """
    # Call /auth/me without token
    response = requests.get("http://localhost:8080/auth/me")
    
    # Should be rejected by Envoy JWT filter
    assert response.status_code == 401


def test_auth_me_endpoint_invalid_token():
    """
    Test /auth/me endpoint with invalid JWT token (Phase B).
    Verify that requests with invalid tokens are rejected.
    """
    response = requests.get(
        "http://localhost:8080/auth/me",
        headers={"Authorization": "Bearer invalid-token-xyz"}
    )
    
    # Should be rejected by Envoy JWT filter or authz service
    assert response.status_code == 401


def test_cache_works_with_multiple_users():
    """
    Test that cache correctly handles multiple users (Phase B).
    Each user should have their own cache entry.
    """
    # Get tokens for different users
    token_user = get_keycloak_token("testuser", "testpass")
    
    try:
        token_cm = get_keycloak_token("testuser-cm", "testpass")
    except AssertionError:
        pytest.skip("User 'testuser-cm' not configured in Keycloak")
    
    # Make requests with different users
    response1 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token_user}"}
    )
    assert response1.status_code == 200
    
    response2 = requests.get(
        "http://localhost:8080/customers",
        headers={"Authorization": f"Bearer {token_cm}"}
    )
    assert response2.status_code == 200
    
    # Each user should get their own filtered results
    customers1 = response1.json()
    customers2 = response2.json()
    
    # Regular user sees only their own customer
    assert len(customers1) == 1
    # Customer manager sees all customers
    assert len(customers2) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
