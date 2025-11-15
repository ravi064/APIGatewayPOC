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

# Setup logging
logger = setup_logging("authz-service")

# Initialize FastAPI app
app = FastAPI(
    title="Authorization Service",
    description="External authorization service for role lookup",
    version="1.0.0"
)

def decode_email_from_jwt(token: str) -> str:
    """
    Decode JWT payload and extract the email claim.

    This function is web-agnostic and raises plain exceptions (ValueError,
    json.JSONDecodeError) on invalid tokens. Callers at the HTTP layer should
    catch these and translate to HTTP responses as appropriate.

    Args:
        token: JWT token string (without 'Bearer ' prefix)

    Returns:
        User email address from JWT 'email' claim

    Raises:
        ValueError: If token format invalid or email claim missing
        json.JSONDecodeError: If payload is not valid JSON
    """
    # JWT structure: header.payload.signature
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    # Decode the payload (add padding if needed)
    payload_part = parts[1]
    padding = 4 - (len(payload_part) % 4)
    if padding != 4:
        payload_part += '=' * padding

    decoded_bytes = base64.urlsafe_b64decode(payload_part)
    payload = json.loads(decoded_bytes)

    email = payload.get('email')
    if not email:
        raise ValueError("Email claim not found in JWT payload")

    return email


def extract_email_from_authorization_header(request: Request, request_id: Optional[str] = None) -> Optional[str]:
    """
    Parse the Authorization header and extract email from the JWT.

    This is a request-level helper: it reads "Authorization: Bearer <token>",
    calls the JWT decoder, and returns the email or None on any client-side
    problem (missing header, invalid format, invalid token).

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
        email = decode_email_from_jwt(token)
        if request_id:
            logger.info(f"[{request_id}] User email extracted: {email}")
        else:
            logger.info(f"User email extracted: {email}")
        return email
    except Exception as e:
        # Decoder raises ValueError / JSON errors; treat as client-side failure
        if request_id:
            logger.info(f"[{request_id}] JWT extraction failed. Reason: {e}")
        else:
            logger.info(f"JWT extraction failed. Reason: {e}")
        return None


def lookup_user_roles(email: str, request_id: Optional[str] = None) -> list:
    """
    Unified role lookup logic for endpoints.

    Queries data access layer (which handles caching internally).
    Returns 'unverified-user' role if user not found in database.

    Args:
        email: User email address
        request_id: Optional request ID for logging correlation

    Returns:
        List of role names (defaults to ['unverified-user'] if user not found)
    """
    try:
        roles = get_user_roles(email)
        if request_id:
            logger.info(f"[{request_id}] Roles retrieved for {email}: {roles}")
        return roles
    except UserNotFoundException:
        if request_id:
            logger.info(f"[{request_id}] No DB entry for {email}. Returning role 'unverified-user'.")
        else:
            logger.info(f"No DB entry for {email}. Returning role 'unverified-user'.")
        return ["unverified-user"]


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

    Note: Data access layer handles caching transparently.
    """
    logger.info("User info request received (/authz/me)")

    # Extract email from request (returns None if no valid JWT)
    email = extract_email_from_authorization_header(request)

    # If no valid JWT, return guest user
    if not email:
        logger.info("Returning guest user for /authz/me request")
        return {
            "email": "",
            "roles": ["guest"]
        }

    # Lookup roles for authenticated user (cache handled by data layer)
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
          Data access layer handles caching transparently.

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
        email = extract_email_from_authorization_header(request, request_id)

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

        # Lookup roles for authenticated user (cache handled by data layer)
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
