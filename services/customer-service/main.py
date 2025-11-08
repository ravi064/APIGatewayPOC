from fastapi import FastAPI, HTTPException, Depends, status
from typing import List
import os
import sys
sys.path.append('/app')

from models.customer import CustomerResponse
from shared.common import setup_logging, create_health_response
from shared.auth import get_current_user_from_headers, JWTPayload
from customer_data_access import customer_data_access

# Setup logging
logger = setup_logging("customer-service")

app = FastAPI(
    title="Customer Service",
    description="Microservice for managing customers",
    version="1.0.0"
)

@app.get("/customers/health")
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return create_health_response("customer-service")

@app.get("/customers", response_model=List[CustomerResponse])
def get_customers(current_user: JWTPayload = Depends(get_current_user_from_headers)):
    """
    Get customers based on user authorization
    
    Authorization:
    - Users with 'guest' role are denied access
    - Users with 'customer-manager' role can retrieve all customers
    - Other users can only retrieve their own customer record (email must match)
    
    Note: Roles are provided by authz-service via X-User-Roles header (set by Envoy)
    """
    logger.info(f"Fetching customers (requested by: {current_user.email})")

    # Check authorization
    # 1. Deny access for 'guest' role
    if current_user.has_role("guest"):
        logger.warning(f"Access denied: User {current_user.email} has 'guest' role and cannot access customers.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Guests are not allowed to access customer data."
        )
    # 2. If user has 'customer-manager' role, they can view all customers
    if current_user.has_role("customer-manager"):
        customers = customer_data_access.get_all_customers()
        logger.info(f"Access granted: User {current_user.email} has customer-manager role - returning all customers")
        logger.info(f"Returning all customers. Count: {customer_data_access.get_customer_count()}")
        return customers

    # 3. Otherwise, filter to only return the customer record that matches the user's email
    user_customers = customer_data_access.get_customers_by_email(current_user.email)

    logger.info(f"Access restricted: User {current_user.email} can only see their own record - returning {len(user_customers)} customer(s)")

    return user_customers

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user: JWTPayload = Depends(get_current_user_from_headers)):
    """
    Get a specific customer by ID
    
    Authorization:
    - Users with 'guest' role are denied access
    - Users with 'customer-manager' role can retrieve any customer
    - Other users can only retrieve their own customer record (email must match)
    
    Note: Roles are provided by authz-service via X-User-Roles header (set by Envoy)
    """
    logger.info(f"Fetching customer with ID: {customer_id} (requested by: {current_user.email})")

    # Check authorization
    # 1. Deny access for 'guest' role
    if current_user.has_role("guest"):
        logger.warning(f"Access denied: User {current_user.email} has 'guest' role and cannot access customer {customer_id}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Guests are not allowed to access customer data."
        )

    # Find the customer using data access layer
    customer = customer_data_access.get_customer_by_id(customer_id)

    # 2. If user has 'customer-manager' role, they can view any customer (even if not found)
    if current_user.has_role("customer-manager"):
        if customer:
            logger.info(f"Access granted: User {current_user.email} has customer-manager role")
            return customer
        else:
            logger.warning(f"Access denied: User {current_user.email} has customer-manager role but customer {customer_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view this customer."
            )

    # 3. Otherwise, check if the customer email matches the user's email
    if customer and customer.email.lower() == current_user.email.lower():
        logger.info(f"Access granted: User {current_user.email} accessing their own record")
        return customer

    # 4. Deny access - user is not a customer-manager and email doesn't match, or customer not found
    logger.warning(
        f"Access denied: User {current_user.email} attempted to access customer {customer_id} "
        f"(customer email: {customer.email if customer else 'N/A'})"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: You are not authorized to view this customer."
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8000))
    logger.info(f"Starting customer service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)