"""
Mock data access layer simulating PostgreSQL role queries.
In production, this would connect to actual PostgreSQL database.

This layer owns all caching decisions - cache-aside pattern with Redis.
"""

from typing import List, Optional
import logging
from redis_cache import get_cache_instance, PlatformRolesCache

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

# Initialize cache at module level (may be None if Redis not configured)
_cache: Optional[PlatformRolesCache] = get_cache_instance()


class UserNotFoundException(Exception):
    """Raised when user email not found in role database"""
    pass


def get_user_roles(email: str) -> List[str]:
    """
    Get roles for a user by email.
    
    Uses cache-aside pattern:
    1. Check cache first
    2. On cache miss, query database
    3. Store result in cache for future requests
    
    Args:
        email: User email address (case-insensitive)
    
    Returns:
        List of role names
    
    Raises:
        UserNotFoundException: If user not found in database
    """
    email_lower = email.lower()
    
    # 1. Try cache first
    if _cache:
        cached_roles = _cache.get(email_lower)
        if cached_roles is not None:
            logger.info(f"Cache HIT: Retrieved roles for {email} from cache: {cached_roles}")
            return cached_roles
        logger.info(f"Cache MISS: {email} not in cache, querying database")
    
    # 2. Cache miss or cache disabled - query database
    roles = USER_ROLES_DB.get(email_lower)
    
    if roles is None:
        logger.warning(f"User not found in role database: {email}")
        raise UserNotFoundException(f"No roles found for user: {email}")
    
    logger.info(f"Database query: Retrieved roles for {email}: {roles}")
    
    # 3. Store in cache for future requests
    if _cache:
        _cache.set(email_lower, roles)
        logger.info(f"Cached roles for {email}")
    
    return roles


def invalidate_user_roles_cache(email: str) -> bool:
    """
    Invalidate cached roles for a user.
    
    Use this when user roles are updated or deleted.
    Safe to call even if cache is disabled or user not cached.
    
    Args:
        email: User email address
    
    Returns:
        True if cache entry was invalidated, False if no entry existed or cache disabled
    """
    if not _cache:
        logger.debug(f"Cache disabled - no invalidation needed for {email}")
        return False
    
    email_lower = email.lower()
    result = _cache.invalidate(email_lower)
    
    if result:
        logger.info(f"Invalidated cache for {email}")
    else:
        logger.debug(f"No cache entry to invalidate for {email}")
    
    return result


def get_cache_health() -> dict:
    """
    Get cache health status.
    
    Returns:
        Dictionary with cache status information
    """
    if not _cache:
        return {
            "cache_enabled": False,
            "cache_healthy": None
        }
    
    return {
        "cache_enabled": True,
        "cache_healthy": _cache.health_check()
    }


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
