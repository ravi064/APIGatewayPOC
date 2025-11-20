# Product Service: All users, including 'guest', have access to product information.
# There are no role-based restrictions on any endpoint in this service.
# User info is only used for logging and future fine-grained authorization if needed.

from fastapi import FastAPI, HTTPException, Depends
from typing import List
import os
import sys
sys.path.append('/app')

from models.product import ProductResponse
from shared.common import setup_logging, create_health_response
from shared.auth import get_current_user, UserInfo
from product_data_access import product_data_access

# Setup logging
logger = setup_logging("product-service")

app = FastAPI(
    title="Product Service",
    description="Microservice for managing products",
    version="1.0.0"
)

@app.get("/products/health")
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return create_health_response("product-service")

@app.get("/products", response_model=List[ProductResponse])
def get_products(current_user: UserInfo = Depends(get_current_user)):
    """
    Get all products

    All roles, including 'guest', can access this endpoint.
    No restrictions on who can see product information.
    User information available for logging and future fine-grained authorization.
    Roles are provided by authz-service via x-user-roles header (set by Envoy).
    """
    logger.info(f"Fetching all products (requested by: {current_user.email}, roles: {current_user.roles})")
    
    products = product_data_access.get_all_products()
    logger.info(f"Returning all products. Count: {product_data_access.get_product_count()}")
    
    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, current_user: UserInfo = Depends(get_current_user)):
    """
    Get a specific product by ID

    All roles, including 'guest', can access this endpoint.
    No restrictions on who can see product information.
    User information available for logging and future fine-grained authorization.
    Roles are provided by authz-service via x-user-roles header (set by Envoy).
    """
    logger.info(f"Fetching product with ID: {product_id} (requested by: {current_user.email})")
    
    # Find the product using data access layer
    product = product_data_access.get_product_by_id(product_id)
    if not product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info(f"Successfully retrieved product: {product.name}")
    return product

@app.get("/products/category/{category}", response_model=List[ProductResponse])
def get_products_by_category(category: str, current_user: UserInfo = Depends(get_current_user)):
    """
    Get products by category

    All roles, including 'guest', can access this endpoint.
    No restrictions on who can see product information.
    User information available for logging and future fine-grained authorization.
    Roles are provided by authz-service via x-user-roles header (set by Envoy).
    """
    logger.info(f"Fetching products by category: {category} (requested by: {current_user.email})")
    
    filtered_products = product_data_access.get_products_by_category(category)
    logger.info(f"Found {len(filtered_products)} products in category: {category}")
    
    return filtered_products

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8000))
    logger.info(f"Starting product service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)