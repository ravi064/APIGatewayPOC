"""
External Authorization Service
Provides role lookup for authenticated users based on email from JWT.

This service is called by Envoy's ext_authz filter to retrieve user roles
from a PostgreSQL database (currently mocked). Roles are returned in response
headers and used by Envoy's RBAC filter for authorization decisions.
"""

import sys
from fastapi import FastAPI, Request, HTTPException, Response
import os
import json
import base64
from typing import Optional
sys.path.append('/app')

from authz_data_access import get_user_roles, UserNotFoundException
from shared.common import setup_logging, create_health_response
from redis_cache import get_cache_instance, PlatformRolesCache

# Setup logging
logger = setup_logging("authz-service")

# Initialize cache (may be None if Redis not configured)
cache: PlatformRolesCache | None = get_cache_instance()

def extract_email_from_request(request: Request, request_id: Optional[str] = None) -> Optional[str]:
    """
    Extract email from JWT token in request authorization header.
    
    Handles all JWT extraction logic including header parsing and token decoding.
    Returns None if no authorization header, invalid format, or JWT decoding fails.
    
    Args:
        request: FastAPI Request object
        request_id: Optional request ID for logging correlation
    
    Returns:
        User email if valid JWT found, None otherwise
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        if request_id:
            logger.info(f"[{request_id}] No authorization header found.")
        else:
            logger.info("No authorization header found.")
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        if request_id:
            logger.info(f"[{request_id}] Authorization header format invalid.")
        else:
            logger.info("Authorization header format invalid.")
        return None
    
    token = parts[1]
    try:
        email = extract_email_from_jwt(token)
        if request_id:
            logger.info(f"[{request_id}] User email extracted: {email}")
        else:
            logger.info(f"User email extracted: {email}")
        return email
    except Exception as e:
        if request_id:
            logger.info(f"[{request_id}] JWT extraction failed. Reason: {e}")
        else:
            logger.info(f"JWT extraction failed. Reason: {e}")
        return None


def lookup_user_roles(email: str, request_id: Optional[str] = None) -> list:
    """
    Unified role lookup logic for endpoints.
    Checks cache, queries DB, handles cache miss, defaults to 'unverified-user'.
    Optionally logs with request_id for correlation.
    """
    roles = None
    if cache:
        roles = cache.get(email)
        if request_id:
            logger.info(f"[{request_id}] Cache lookup for {email}: {roles}")
    if roles is None:
        try:
            roles = get_user_roles(email)
            if cache and roles:
                cache.set(email, roles)
            if request_id:
                logger.info(f"[{request_id}] DB lookup for {email}: {roles}")
        except UserNotFoundException:
            if request_id:
                logger.info(f"[{request_id}] No DB entry for {email}. Returning role 'unverified-user'.")
            roles = ["unverified-user"]
    if not roles:
        if request_id:
            logger.info(f"[{request_id}] No roles found for {email}. Returning role 'unverified-user'.")
        roles = ["unverified-user"]
    return roles

app = FastAPI(
    title="Authorization Service",
    description="External authorization service for role lookup",
    version="1.0.0"
)


def extract_email_from_jwt(token: str) -> str:
    """
    Extract email from JWT payload.
    
    Note: JWT signature is already validated by Envoy's JWT filter.
    We only decode the payload to extract user information.
    
    Args:
        token: JWT token string (without 'Bearer ' prefix)
    
    Returns:
        User email address from JWT 'email' claim
    
    Raises:
        HTTPException: If token cannot be decoded or email claim missing
    """
    try:
        # JWT structure: header.payload.signature
        # We only need the payload (middle part)
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Decode the payload (add padding if needed)
        payload_part = parts[1]
        # Add padding if needed for base64 decoding
        padding = 4 - (len(payload_part) % 4)
        if padding != 4:
            payload_part += '=' * padding
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)
        
        # Extract email
        email = payload.get('email')
        if not email:
            raise ValueError("Email claim not found in JWT payload")
        
        return email
    
    except (ValueError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to extract email from JWT: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )


@app.get("/authz/health")
def health_check():
    """
    Health check endpoint.
    
    Used by Docker healthcheck and Envoy health checking.
    Includes Redis cache health status if caching is enabled.
    
    Returns:
        Health status information
    """
    logger.info("Health check requested")
    response = create_health_response("authz-service")
    
    # Add cache health status if caching is enabled
    if cache:
        response["cache_enabled"] = True
        response["cache_healthy"] = cache.health_check()
    else:
        response["cache_enabled"] = False
    
    return response

@app.get("/authz/me")
async def get_current_user(request: Request):
    """
    Get current user information and roles.
    
    Public endpoint for React UI to fetch authenticated user's email and platform roles.
    Returns guest role if no valid JWT token is provided.
    
    Request Headers:
        authorization: Bearer <jwt-token> (optional)
    
    Returns:
        200 OK: User information with roles
        {
            "email": "user@example.com",
            "roles": ["user", "customer-manager"]
        }
        
        Or for unauthenticated requests:
        {
            "email": "",
            "roles": ["guest"]
        }
    
    Note: This endpoint uses the same role lookup logic as ext_authz,
          including Redis caching for performance.
    """
    logger.info("User info request received (/authz/me)")
    
    # Extract email from request (returns None if no valid JWT)
    email = extract_email_from_request(request)
    
    # If no valid JWT, return guest user
    if not email:
        logger.info("Returning guest user for /authz/me request")
        return {
            "email": "",
            "roles": ["guest"]
        }
    
    # Lookup roles for authenticated user
    logger.info(f"User info request for email: {email}")
    roles = lookup_user_roles(email)
    logger.info(f"Returning user info for {email}: roles={roles}")
    return {
        "email": email,
        "roles": roles
    }

@app.api_route("/authz/roles", methods=["GET", "POST"])
@app.api_route("/authz/roles/{path:path}", methods=["GET", "POST"])
async def get_user_roles_endpoint(request: Request, path: Optional[str] = None):
    """
    Role lookup endpoint called by Envoy ext_authz filter.
    
    Accepts both GET and POST methods (Envoy may use either depending on original request).
    Accepts both /authz/roles and /authz/roles/* paths.
    The path suffix (e.g., /customers, /products) is ignored and can be used
    for logging/debugging purposes. This allows Envoy's path_prefix to work
    correctly with ext_authz filter.
    
    Extracts user email from JWT token and returns roles in response headers.
    This endpoint is only called by Envoy after JWT validation.
    
    Request Headers:
        authorization: Bearer <jwt-token> (validated by Envoy)
        x-request-id: <uuid> (optional, for request tracing)
    
    Response Headers (200 OK, HTTP/2 lowercase):
        x-user-email: user@example.com
        x-user-roles: user,customer-manager (comma-separated, NO spaces or whitespace)
    
    Note: Role names must contain only printable characters (no whitespace).
          Multiple roles are returned as a comma-separated list with NO spaces
          between role names (e.g., "user,customer-manager" not "user, customer-manager").
    
    Args:
        path: Optional path suffix from original request (e.g., "customers", "products")
              This is ignored but logged for debugging.
    
    Returns:
        200 OK: User found, roles returned in headers
        500 Internal Server Error: Service error
    """
    # Extract request ID for logging correlation
    request_id = request.headers.get("x-request-id", "unknown")
    
    # Log the original request path for debugging
    if path:
        logger.info(f"[{request_id}] AuthZ role lookup request ({request.method}) for path: /{path}")
    else:
        logger.info(f"[{request_id}] AuthZ role lookup request ({request.method}) received")
    
    try:
        # Extract email from request (returns None if no valid JWT)
        email = extract_email_from_request(request, request_id)
        
        # If no valid JWT, return guest role
        if not email:
            logger.info(f"[{request_id}] Returning role 'guest'.")
            return Response(
                status_code=200,
                content="",
                headers={
                    "x-user-email": "",
                    "x-user-roles": "guest"
                }
            )
        
        # Lookup roles for authenticated user
        roles = lookup_user_roles(email, request_id)
        if not roles:
            logger.info(f"[{request_id}] No roles found for {email}. Returning role 'unverified-user'.")
            return Response(
                status_code=200,
                content="",
                headers={
                    "x-user-email": email,
                    "x-user-roles": "unverified-user"
                }
            )
        roles_str = ",".join(roles)
        logger.info(f"[{request_id}] Roles found for {email}: {roles}")
        return Response(
            status_code=200,
            content="",
            headers={
                "x-user-email": email,
                "x-user-roles": roles_str
            }
        )
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected authorization error: {e}", exc_info=True)
        return Response(
            status_code=500,
            content="Internal authorization error",
            headers={}
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 9000))
    logger.info(f"Starting authorization service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
