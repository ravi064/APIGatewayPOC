"""
Mock data access layer simulating PostgreSQL role queries.
In production, this would connect to actual PostgreSQL database.
"""

from typing import List
import logging

logger = logging.getLogger(__name__)

# Mock database: user email -> roles mapping
# Simulates PostgreSQL table: user_roles (email VARCHAR PRIMARY KEY, roles TEXT[])
USER_ROLES_DB = {
    "test.user-vrfd@example.com": ["verified-user"],
    "test.user@example.com": ["user"],
    "test.user-cm@example.com": ["user", "customer-manager"],
    "test.user-pm@example.com": ["user", "product-manager"],
    "test.user-pcm@example.com": ["user", "product-category-manager"],
    "admin.user@example.com": ["user", "admin"]
}


class UserNotFoundException(Exception):
    """Raised when user email not found in role database"""
    pass


def get_user_roles(email: str) -> List[str]:
    """
    Get roles for a user by email.
    
    Simulates: SELECT roles FROM user_roles WHERE email = ?
    
    Args:
        email: User email address (case-insensitive)
    
    Returns:
        List of role names
    
    Raises:
        UserNotFoundException: If user not found in database
    """
    email_lower = email.lower()
    roles = USER_ROLES_DB.get(email_lower)
    
    if roles is None:
        logger.warning(f"User not found in role database: {email}")
        raise UserNotFoundException(f"No roles found for user: {email}")
    
    logger.info(f"Retrieved roles for {email}: {roles}")
    return roles


def get_all_users() -> dict:
    """
    Get all users (for debugging/testing only).
    
    Returns:
        Dictionary of email -> roles mapping
    """
    return USER_ROLES_DB.copy()


def get_user_count() -> int:
    """
    Get count of users in database.
    
    Returns:
        Number of users
    """
    return len(USER_ROLES_DB)
