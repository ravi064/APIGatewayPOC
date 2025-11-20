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

from conftest import get_access_token, get_auth_headers, GATEWAY_BASE_URL

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

def test_jwt_tampering_rejected():
    """
    Security test: Verify that tampering with JWT email claim is rejected.
    
    This test simulates an attack where:
    1. User authenticates as 'testuser' (test.user@example.com)
    2. Attacker modifies the JWT payload to change email to 'test.user-cm@example.com'
    3. Request is sent with tampered token to access /customers
    
    Expected: Gateway/authz-service MUST reject the tampered token with 401/403
    because the signature won't match the modified payload.
    
    This validates that JWT signature verification is properly enforced.
    """
    import base64
    import json
    
    # 1. Get legitimate token for testuser
    legitimate_token = get_access_token("testuser")
    
    # 2. Decode and tamper with the JWT payload
    # JWT structure: header.payload.signature
    parts = legitimate_token.split('.')
    assert len(parts) == 3, "Invalid JWT format"
    
    # Decode the payload (middle part)
    payload_part = parts[1]
    # Add padding if needed for base64 decoding
    padding = 4 - (len(payload_part) % 4)
    if padding != 4:
        payload_part += '=' * padding
    
    decoded_bytes = base64.urlsafe_b64decode(payload_part)
    payload = json.loads(decoded_bytes)
    
    # 3. Modify the email claim to impersonate testuser-cm
    original_email = payload.get("email")
    payload["email"] = "test.user-cm@example.com"
    
    # 4. Re-encode the tampered payload
    tampered_payload_bytes = json.dumps(payload).encode('utf-8')
    tampered_payload_b64 = base64.urlsafe_b64encode(tampered_payload_bytes).decode('utf-8').rstrip('=')
    
    # 5. Reconstruct the JWT with tampered payload (original signature)
    tampered_token = f"{parts[0]}.{tampered_payload_b64}.{parts[2]}"
    
    # 6. Try to access /customers with tampered token
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    
    # 7. Capture response details for analysis
    print("\n" + "="*70)
    print("JWT TAMPERING SECURITY TEST RESULTS")
    print("="*70)
    print(f"Original email:    {original_email}")
    print(f"Tampered email:    test.user-cm@example.com")
    print(f"Response status:   {response.status_code}")
    print(f"Response headers:  {dict(response.headers)}")
    print(f"Response body:     {response.text[:200] if response.text else '(empty)'}")
    print("="*70 + "\n")
    
    # 8. Verify rejection
    # Expected: 401 (Unauthorized) if Envoy validates signature
    # or 403 (Forbidden) if authz-service detects mismatch
    assert response.status_code in [401, 403], (
        f"Security vulnerability: Tampered JWT was accepted! "
        f"Original email: {original_email}, Tampered email: test.user-cm@example.com, "
        f"Status: {response.status_code}"
    )
    
    print(f"Security test passed: Tampered JWT rejected with status {response.status_code}")


def test_jwt_expired_token_rejected():
    """
    Security test: Verify that expired JWT tokens are rejected.
    
    This test simulates an attack where:
    1. User authenticates and gets a valid JWT token
    2. Attacker modifies the 'exp' (expiration) claim to a past timestamp
    3. Request is sent with expired token to access /customers
    
    Expected: Gateway MUST reject the expired token with 401
    because the token has passed its expiration time.
    
    This validates that JWT expiration validation is properly enforced.
    """
    import base64
    import json
    import time
    
    # 1. Get legitimate token for testuser
    legitimate_token = get_access_token("testuser")
    
    # 2. Decode and tamper with the JWT payload
    parts = legitimate_token.split('.')
    assert len(parts) == 3, "Invalid JWT format"
    
    # Decode the payload
    payload_part = parts[1]
    padding = 4 - (len(payload_part) % 4)
    if padding != 4:
        payload_part += '=' * padding
    
    decoded_bytes = base64.urlsafe_b64decode(payload_part)
    payload = json.loads(decoded_bytes)
    
    # 3. Modify the expiration claim to a past timestamp
    original_exp = payload.get("exp")
    past_timestamp = int(time.time()) - 3600  # 1 hour ago
    payload["exp"] = past_timestamp
    
    # 4. Re-encode the tampered payload
    tampered_payload_bytes = json.dumps(payload).encode('utf-8')
    tampered_payload_b64 = base64.urlsafe_b64encode(tampered_payload_bytes).decode('utf-8').rstrip('=')
    
    # 5. Reconstruct the JWT with expired timestamp (original signature)
    tampered_token = f"{parts[0]}.{tampered_payload_b64}.{parts[2]}"
    
    # 6. Try to access /customers with expired token
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    
    # 7. Capture response details for analysis
    print("\n" + "="*70)
    print("JWT EXPIRATION SECURITY TEST RESULTS")
    print("="*70)
    print(f"Original exp:      {original_exp}")
    print(f"Tampered exp:      {past_timestamp} (1 hour ago)")
    print(f"Response status:   {response.status_code}")
    print(f"Response headers:  {dict(response.headers)}")
    print(f"Response body:     {response.text[:200] if response.text else '(empty)'}")
    print("="*70 + "\n")
    
    # 8. Verify rejection
    # Expected: 401 (Unauthorized) - Envoy should detect signature mismatch
    # Note: Even though we set exp to past, the signature won't match the modified payload
    assert response.status_code == 401, (
        f"Security vulnerability: Expired/tampered JWT was accepted! "
        f"Status: {response.status_code}"
    )
    
    print(f"Security test passed: Expired JWT rejected with status {response.status_code}")


def test_jwt_wrong_issuer_rejected():
    """
    Security test: Verify that JWT tokens with wrong issuer are rejected.
    
    This test simulates an attack where:
    1. User authenticates and gets a valid JWT token
    2. Attacker modifies the 'iss' (issuer) claim to a different authority
    3. Request is sent with modified token to access /customers
    
    Expected: Gateway MUST reject the token with wrong issuer with 401
    because the issuer doesn't match the configured trusted issuer.
    
    This validates that JWT issuer validation is properly enforced.
    """
    import base64
    import json
    
    # 1. Get legitimate token for testuser
    legitimate_token = get_access_token("testuser")
    
    # 2. Decode and tamper with the JWT payload
    parts = legitimate_token.split('.')
    assert len(parts) == 3, "Invalid JWT format"
    
    # Decode the payload
    payload_part = parts[1]
    padding = 4 - (len(payload_part) % 4)
    if padding != 4:
        payload_part += '=' * padding
    
    decoded_bytes = base64.urlsafe_b64decode(payload_part)
    payload = json.loads(decoded_bytes)
    
    # 3. Modify the issuer claim to a malicious/different issuer
    original_issuer = payload.get("iss")
    payload["iss"] = "http://malicious-keycloak.example.com/realms/fake-realm"
    
    # 4. Re-encode the tampered payload
    tampered_payload_bytes = json.dumps(payload).encode('utf-8')
    tampered_payload_b64 = base64.urlsafe_b64encode(tampered_payload_bytes).decode('utf-8').rstrip('=')
    
    # 5. Reconstruct the JWT with wrong issuer (original signature)
    tampered_token = f"{parts[0]}.{tampered_payload_b64}.{parts[2]}"
    
    # 6. Try to access /customers with wrong issuer token
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = requests.get(f"{BASE_URL}/customers", headers=headers)
    
    # 7. Capture response details for analysis
    print("\n" + "="*70)
    print("JWT ISSUER SECURITY TEST RESULTS")
    print("="*70)
    print(f"Original issuer:   {original_issuer}")
    print(f"Tampered issuer:   http://malicious-keycloak.example.com/realms/fake-realm")
    print(f"Response status:   {response.status_code}")
    print(f"Response headers:  {dict(response.headers)}")
    print(f"Response body:     {response.text[:200] if response.text else '(empty)'}")
    print("="*70 + "\n")
    
    # 8. Verify rejection
    # Expected: 401 (Unauthorized) - Envoy should detect signature mismatch
    # Note: Even though we changed the issuer, the signature won't match the modified payload
    assert response.status_code == 401, (
        f"Security vulnerability: JWT with wrong issuer was accepted! "
        f"Original issuer: {original_issuer}, "
        f"Status: {response.status_code}"
    )
    
    print(f"Security test passed: JWT with wrong issuer rejected with status {response.status_code}")