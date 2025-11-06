"""
Customer Data Access Layer
Handles all data operations for customers (currently mock data, future: database)
"""
from typing import List, Optional
from datetime import datetime
from models.customer import Customer


class CustomerDataAccess:
    """Data access class for customer operations"""
    
    def __init__(self):
        # Mock data for now (will be replaced with database)
        self._customers_db = [
            Customer(
                id=1,
                name="Test User-unvrfd",
                email="test.user-unvrfd@example.com",
                phone="+1234567891",
                created_at=datetime.now()
            ),
            Customer(
                id=2,
                name="Test User-vrfd",
                email="test.user-vrfd@example.com",
                phone="+1234567892",
                created_at=datetime.now()
            ),
            Customer(
                id=3,
                name="Test User",
                email="test.user@example.com",
                phone="+1234567893",
                created_at=datetime.now()
            ),
            Customer(
                id=4,
                name="Test User-cm",
                email="test.user-cm@example.com",
                phone="+1234567894",
                created_at=datetime.now()
            ),
            Customer(
                id=5,
                name="Test User-pm",
                email="test.user-pm@example.com",
                phone="+1234567895",
                created_at=datetime.now()
            ),
            Customer(
                id=6,
                name="Test User-pcm",
                email="test.user-pcm@example.com",
                phone="+1234567896",
                created_at=datetime.now()
            ),
            Customer(
                id=7,
                name="Admin User",
                email="admin.user@example.com",
                phone="+1234567897",
                created_at=datetime.now()
            )
        ]
    
    def get_all_customers(self) -> List[Customer]:
        """
        Retrieve all customers from the data store
        
        Returns:
            List[Customer]: All customers in the system
        """
        return self._customers_db.copy()
    
    def get_customers_by_email(self, email: str) -> List[Customer]:
        """
        Retrieve customers filtered by email (case-insensitive)
        
        Args:
            email: Email address to filter by
            
        Returns:
            List[Customer]: Customers matching the email address
        """
        return [
            customer for customer in self._customers_db 
            if customer.email.lower() == email.lower()
        ]
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        Retrieve a specific customer by ID
        
        Args:
            customer_id: The customer ID to search for
            
        Returns:
            Optional[Customer]: The customer if found, None otherwise
        """
        return next(
            (customer for customer in self._customers_db if customer.id == customer_id), 
            None
        )
    
    def get_customer_count(self) -> int:
        """
        Get the total number of customers
        
        Returns:
            int: Total customer count
        """
        return len(self._customers_db)


# Global instance for dependency injection
customer_data_access = CustomerDataAccess()