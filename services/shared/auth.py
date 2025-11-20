"""
Authentication utilities for JWT token handling and role extraction from headers.

This module supports the external authorization service architecture where:
1. Envoy validates JWT tokens
2. Envoy calls authz-service to retrieve user roles from database
3. Envoy forwards requests with x-user-email and x-user-roles headers
4. Backend services extract user info from these headers

Important: HTTP/2 headers (used by Envoy) are lowercase.
"""
import base64
import json
from typing import Dict, List, Optional
from fastapi import Header, HTTPException, status


class UserInfo:
    """
    Base class for user information.
    
    Contains common user attributes and role-checking helper methods.
    All authentication methods return instances of this class or its subclasses.
    """
    
    def __init__(
        self,
        email: str,
        roles: List[str],
        preferred_username: Optional[str] = None,
        name: Optional[str] = None,
        sub: Optional[str] = None
    ):
        self.email = email
        self.roles = roles
        self.preferred_username = preferred_username
        self.name = name
        self.sub = sub
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)
    
    def __repr__(self):
        return f"{self.__class__.__name__}(email={self.email}, roles={self.roles})"


class JWTUserInfo(UserInfo):
    """
    User information extracted from JWT token only (standalone mode).
    
    This is the legacy/educational pattern where roles are embedded in JWT claims.
    In production, use HeaderUserInfo which gets roles from external authz service.
    
    Roles are extracted from JWT 'realm_access.roles' claim.
    """
    
    def __init__(self, jwt_payload: Dict):
        realm_access = jwt_payload.get("realm_access", {})
        roles = realm_access.get("roles", [])
        
        super().__init__(
            email=jwt_payload.get("email", ""),
            roles=roles,
            preferred_username=jwt_payload.get("preferred_username"),
            name=jwt_payload.get("name"),
            sub=jwt_payload.get("sub")
        )
        self.jwt_payload = jwt_payload  # Keep raw payload if needed


class HeaderUserInfo(UserInfo):
    """
    User information from Envoy external authz headers (recommended).
    
    This is the current architecture where:
    - JWT provides user identity (email, name, etc.)
    - Roles come from x-user-roles header (populated by authz-service via Envoy)
    - Email from x-user-email header is preferred (source of truth from authz-service)
    
    Supports both authenticated users (with JWT) and guest users (without JWT).
    Guest users have roles=["guest"] set by authz-service.
    """
    
    def __init__(
        self,
        jwt_payload: Optional[Dict],
        header_roles: List[str],
        header_email: Optional[str] = None
    ):
        # For guest users, jwt_payload is None
        if jwt_payload is None:
            super().__init__(
                email=header_email or "",
                roles=header_roles,
                preferred_username="guest",
                name="Guest User",
                sub="guest"
            )
        else:
            # For authenticated users, prefer header email over JWT email
            email = header_email or jwt_payload.get("email", "")
            super().__init__(
                email=email,
                roles=header_roles,  # Roles always come from authz-service via headers
                preferred_username=jwt_payload.get("preferred_username"),
                name=jwt_payload.get("name"),
                sub=jwt_payload.get("sub")
            )
            self.jwt_payload = jwt_payload


def _extract_bearer_token(authorization: str) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
    
    Returns:
        JWT token string
    
    Raises:
        HTTPException: If header format is invalid
    """
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    return parts[1]


def _decode_jwt_payload(token: str) -> Dict:
    """
    Decode JWT token payload without verification.
    
    Note: This assumes the token has already been validated by Envoy.
    We only decode to extract user information (email, name, etc.).
    
    Args:
        token: JWT token string (without 'Bearer ' prefix)
    
    Returns:
        Decoded JWT payload dictionary
    
    Raises:
        HTTPException: If token cannot be decoded
    """
    try:
        # JWT structure: header.payload.signature
        # We only need the payload (middle part)
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Decode the payload (add padding if needed)
        payload_part = parts[1]
        padding = 4 - (len(payload_part) % 4)
        if padding != 4:
            payload_part += '=' * padding
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)
        
        return payload
    
    except (ValueError, json.JSONDecodeError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user_jwt(
    authorization: str = Header(...)
) -> JWTUserInfo:
    """
    FastAPI dependency to extract user from JWT token only (standalone mode).
    
    EDUCATIONAL: This shows the legacy pattern where roles are in JWT claims.
    Use get_current_user() instead for the external authz architecture.
    
    Args:
        authorization: Authorization header value (required)
    
    Returns:
        JWTUserInfo: User information with roles from JWT
    
    Raises:
        HTTPException: If authorization header is missing or invalid
    
    Usage:
        @app.get("/protected")
        def protected_endpoint(current_user: UserInfo = Depends(get_current_user_jwt)):
            return {"email": current_user.email, "roles": current_user.roles}
    """
    token = _extract_bearer_token(authorization)
    payload = _decode_jwt_payload(token)
    return JWTUserInfo(payload)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None, alias="x-user-email"),
    x_user_roles: Optional[str] = Header(None, alias="x-user-roles")
) -> UserInfo:
    """
    FastAPI dependency to extract current user from Envoy external authz headers.
    
    This is the recommended approach for the external authorization architecture where:
    1. Envoy validates JWT token (optional for guest routes)
    2. Envoy calls authz-service to retrieve user roles from database
    3. Envoy forwards request with x-user-email and x-user-roles headers
    4. This dependency extracts user info from those headers
    
    Supports both authenticated users (with JWT) and guest users (without JWT).
    Guest users will have roles=["guest"] assigned by authz-service.
    
    Security: If an Authorization header is provided, the JWT token MUST be valid.
    Invalid tokens are rejected with 401, not treated as guests.
    
    Headers Expected (set by Envoy, HTTP/2 lowercase):
        authorization: Bearer <jwt-token> (optional, for authenticated users)
        x-user-email: user@example.com (from authz-service, empty for guests)
        x-user-roles: user,customer-manager or guest (comma-separated, from authz-service)
    
    Args:
        authorization: Authorization header value (JWT token, optional)
        x_user_email: User email from authz-service (via Envoy)
        x_user_roles: Comma-separated roles from authz-service (via Envoy)
    
    Returns:
        HeaderUserInfo: User information with roles from authz-service
    
    Raises:
        HTTPException: If authorization is missing and guest role not present, or if token is invalid
    
    Usage:
        @app.get("/protected")
        def protected_endpoint(current_user: UserInfo = Depends(get_current_user)):
            return {"email": current_user.email, "roles": current_user.roles}
    """
    # Parse roles from x-user-roles header (comma-separated, no spaces)
    roles = []
    if x_user_roles:
        roles = [role.strip() for role in x_user_roles.split(",") if role.strip()]
    
    # Handle guest users (no authorization header at all)
    if not authorization:
        # Only allow guest access if authz-service explicitly set "guest" role
        if "guest" in roles:
            return HeaderUserInfo(
                jwt_payload=None,
                header_roles=roles,
                header_email=x_user_email or ""
            )
        else:
            # No authorization and no guest role - deny access
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header"
            )
    
    # Authorization header exists - token MUST be valid
    # Invalid tokens are rejected, not treated as guests
    token = _extract_bearer_token(authorization)
    payload = _decode_jwt_payload(token)
    
    # Return user info with roles from header (authz-service is source of truth)
    return HeaderUserInfo(
        jwt_payload=payload,
        header_roles=roles,
        header_email=x_user_email
    )

