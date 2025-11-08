"""
External Authorization Service
Provides role lookup for authenticated users based on email from JWT.

This service is called by Envoy's ext_authz filter to retrieve user roles
from a PostgreSQL database (currently mocked). Roles are returned in response
headers and used by Envoy's RBAC filter for authorization decisions.
"""

from fastapi import FastAPI, Request, HTTPException, Response
import logging
import os
import json
import base64
from typing import Optional

from authz_data_access import get_user_roles, UserNotFoundException

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "authz-service",
        "version": "1.0.0"
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
        401 Unauthorized: Invalid or missing JWT token
        403 Forbidden: User not found in role database
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
        # Extract and validate Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            logger.warning(f"[{request_id}] Missing authorization header")
            raise HTTPException(
                status_code=401,
                detail="Missing authorization header"
            )
        
        # Extract token from "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"[{request_id}] Invalid authorization header format")
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Expected 'Bearer <token>'"
            )
        
        token = parts[1]
        
        # Decode JWT to get user email
        # Note: Signature already validated by Envoy
        email = extract_email_from_jwt(token)
        logger.info(f"[{request_id}] User email extracted: {email}")
        
        # Lookup roles from database (Phase A: mock data)
        roles = get_user_roles(email)
        roles_str = ",".join(roles)
        
        logger.info(f"[{request_id}] Roles found for {email}: {roles}")
        
        # Return success with roles in headers
        # Envoy will forward these headers to downstream services
        # Note: HTTP/2 headers must be lowercase
        return Response(
            status_code=200,
            content="",  # Empty body
            headers={
                "x-user-email": email,
                "x-user-roles": roles_str
            }
        )
    
    except UserNotFoundException as e:
        logger.warning(f"[{request_id}] User not found: {e}")
        raise HTTPException(
            status_code=403,
            detail=f"User not authorized: {str(e)}"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected authorization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal authorization error"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 9000))
    logger.info(f"Starting authorization service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
