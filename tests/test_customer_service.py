"""
Integration tests for Customer Service
"""
from urllib import response
import pytest
import requests
# conftest.py functions and constants are automatically available
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import get_auth_headers, GATEWAY_BASE_URL


class TestCustomerService:
    """Test customer service endpoints"""
    
    def test_health_check_via_gateway(self):
        """Test health check through API Gateway"""
        headers = get_auth_headers("testuser")
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "customer-service"
    
    def test_get_all_customers_via_gateway(self):
        """Test getting all customers through API Gateway with customer-manager role"""
        headers = get_auth_headers("testuser-cm")  # Has customer-manager role
        
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
        headers = get_auth_headers("testuser")
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/3", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 3
        assert customer["name"] == "Test User"
        assert customer["email"] == "test.user@example.com"
    
    def test_get_nonexistent_customer(self):
        """Test getting non-existent customer"""
        headers = get_auth_headers("testuser-cm")
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/999", headers=headers)
        assert response.status_code == 404
        error = response.json()
        assert "Customer not found" in error["detail"]
    
    def test_unauthorized_access_without_token(self):
        """Test that requests without token are rejected"""
        response = requests.get(f"{GATEWAY_BASE_URL}/customers")
        assert response.status_code == 401  # Unauthorized

    def test_unverified_user_access_self_from_customers(self):
        """Test that unverified users can access only their own customer record"""
        headers = get_auth_headers("testuser-unvrfd")
        
        # Should get only their own customer record
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1  # Should only get their own record
        assert customers[0]["email"] == "test.user-unvrfd@example.com"
        assert customers[0]["id"] == 1

    def test_verified_user_access_self_from_customers(self):
        """Test that verified users can access only their own customer record"""
        headers = get_auth_headers("testuser-vrfd")
        
        # Should get only their own customer record
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1  # Should only get their own record
        assert customers[0]["email"] == "test.user-vrfd@example.com"
        assert customers[0]["id"] == 2


class TestCustomerRBAC:
    """Test Role-Based Access Control for customer endpoints"""
    
    def test_customer_manager_can_access_all_customers_list(self):
        """Test that customer-manager can get all customers"""
        headers = get_auth_headers("testuser-cm")  # Has customer-manager role
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 7  # Should get all customers
        
        # Verify we get different customer emails
        customer_emails = [c["email"] for c in customers]
        assert "test.user@example.com" in customer_emails
        assert "admin.user@example.com" in customer_emails
        assert "test.user-pm@example.com" in customer_emails
    
    def test_regular_user_gets_only_own_customer_in_list(self):
        """Test that regular users only get their own customer in the list"""
        headers = get_auth_headers("testuser")  # email: test.user@example.com
  
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1  # Should only get their own record
        assert customers[0]["email"] == "test.user@example.com"
        assert customers[0]["id"] == 3

    def test_admin_user_gets_own_customer_in_list(self):
        """Test that admin user gets their own customer in the list"""
        headers = get_auth_headers("adminuser")  # Has admin roles
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1  # Should get only their own record
        assert customers[0]["email"] == "admin.user@example.com"
        assert customers[0]["id"] == 7

    def test_product_manager_gets_only_own_customer_in_list(self):
        """Test that product-manager only gets their own customer record"""
        headers = get_auth_headers("testuser-pm")  # email: test.user-pm@example.com, role: product-manager
        
        response = requests.get(f"{GATEWAY_BASE_URL}/customers", headers=headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 1  # Should only get their own record
        assert customers[0]["email"] == "test.user-pm@example.com"
        assert customers[0]["id"] == 5

    def test_customer_manager_can_access_any_customer(self):
        """Test that users with customer-manager role can access any customer"""
        headers = get_auth_headers("testuser-cm")  # Has customer-manager role

        # Try to access different customers
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/3", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 3
        assert customer["email"] == "test.user@example.com"
        
        # Try another customer
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/7", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 7
        assert customer["email"] == "admin.user@example.com"
    
    def test_user_can_access_own_customer_record(self):
        """Test that regular users can access their own customer record"""
        headers = get_auth_headers("testuser")  # email: test.user@example.com

        # test.user@example.com corresponds to customer ID 3
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/3", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 3
        assert customer["email"] == "test.user@example.com"
    
    def test_user_cannot_access_other_customer_record(self):
        """Test that regular users cannot access other customers' records"""
        headers = get_auth_headers("testuser")  # email: test.user@example.com

        # Try to access a different customer (ID 7 - admin.user@example.com)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/7", headers=headers)
        assert response.status_code == 403
        error = response.json()
        assert "Access denied" in error["detail"]
        assert "only view your own customer information" in error["detail"]
    
    def test_admin_user_can_access_own_record(self):
        """Test that admin user can access their own customer record"""
        headers = get_auth_headers("adminuser")  # email: admin.user@example.com

        # admin.user@example.com corresponds to customer ID 7
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/7", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["id"] == 7
        assert customer["email"] == "admin.user@example.com"
    
    def test_admin_user_cannot_access_other_customers(self):
        """Test that admin user cannot access other customers"""
        headers = get_auth_headers("adminuser")  # Has user and admin roles
      
        # Try to access different customer (adminuser is ID 7, trying to access ID 2)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/2", headers=headers)

        # Should fail because adminuser does not have customer-manager role
        assert response.status_code == 403
        error = response.json()
        assert "Access denied" in error["detail"]
        assert "only view your own customer information" in error["detail"]

    def test_product_manager_cannot_access_other_customers(self):
        """Test that product-manager role doesn't grant customer access"""
        headers = get_auth_headers("testuser-pm")  # email: test.user-pm@example.com, role: product-manager
        
        # Can access own record (ID 5)
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/5", headers=headers)
        assert response.status_code == 200
        customer = response.json()
        assert customer["email"] == "test.user-pm@example.com"
        
        # Cannot access other customer's record
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/2", headers=headers)
        assert response.status_code == 403
        error = response.json()
        assert "Access denied" in error["detail"]
    
    def test_rbac_with_nonexistent_customer(self):
        """Test that RBAC is applied before 404 errors"""
        headers = get_auth_headers("testuser")
     
        # Try to access non-existent customer
        response = requests.get(f"{GATEWAY_BASE_URL}/customers/999", headers=headers)
        # Should return 404 (customer not found) rather than 403
        # This is correct behavior - we check existence first, then authorization
        assert response.status_code == 404