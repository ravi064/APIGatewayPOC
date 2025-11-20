"""
Mock data access layer simulating PostgreSQL role queries.
In production, this would connect to actual PostgreSQL database.

This layer owns all caching decisions - cache-aside pattern with Redis.
"""

from typing import Dict, List, Optional
import logging
from redis_cache import get_platform_roles_cache_instance, PlatformRolesCache

logger = logging.getLogger(__name__)

# Mock database: user email -> roles mapping
# Simulates PostgreSQL table: user_roles (email VARCHAR PRIMARY KEY, roles TEXT[])
USER_ROLES_DB: Dict[str, List[str]] = {
    "test.user-vrfd@example.com": ["verified-user"],
    "test.user@example.com": ["user"],
    "test.user-cm@example.com": ["user", "customer-manager"],
    "test.user-pm@example.com": ["user", "product-manager"],
    "test.user-pcm@example.com": ["user", "product-category-manager"],
    "admin.user@example.com": ["user", "admin"]
}


class UserNotFoundException(Exception):
    """Raised when user email not found in role database"""


class AuthDataAccess:
    """Data access wrapper for user role lookups and cache management.

    This class implements a cache-aside pattern:
      1. Try to read roles from cache
      2. On cache miss, read from the backing "database" (mocked here)
      3. Store the result in cache for subsequent requests

    In production, the cache and database would be injected as dependencies.
    For this learning example, we initialize them directly in __init__.
    """

    def __init__(self) -> None:
        """Initialize data access layer with cache and mock database.

        The cache is retrieved from get_platform_roles_cache_instance() which returns None
        if Redis is not configured. The mock database uses the module-level
        USER_ROLES_DB constant.
        """
        self._platform_roles_cache: Optional[PlatformRolesCache] = get_platform_roles_cache_instance()
        self._user_roles_db: Dict[str, List[str]] = USER_ROLES_DB

    def get_user_roles(self, email: str) -> List[str]:
        """Get roles for a user by email (case-insensitive).

        Raises:
            UserNotFoundException: If user not found in database
        """
        email_lower = email.lower()

        # 1. Try cache first
        if self._platform_roles_cache:
            cached_roles = self._platform_roles_cache.get_roles(email_lower)
            if cached_roles is not None:
                logger.info(f"Cache HIT: Retrieved roles for {email} from cache: {cached_roles}")
                return cached_roles
            logger.info(f"Cache MISS: {email} not in cache, querying database")

        # 2. Cache miss or cache disabled - query database
        roles = self._user_roles_db.get(email_lower)

        if roles is None:
            logger.warning(f"User not found in role database: {email}")
            raise UserNotFoundException(f"No roles found for user: {email}")

        logger.info(f"Database query: Retrieved roles for {email}: {roles}")

        # 3. Store in cache for future requests
        if self._platform_roles_cache:
            self._platform_roles_cache.set_roles(email_lower, roles)
            logger.info(f"Cached roles for {email}")

        return roles

    def invalidate_user_roles_cache(self, email: str) -> bool:
        """Invalidate cached roles for a user.

        Returns True if a cache entry was invalidated, False otherwise.
        """
        if not self._platform_roles_cache:
            logger.debug(f"Cache disabled - no invalidation needed for {email}")
            return False

        email_lower = email.lower()
        result = self._platform_roles_cache.invalidate_roles(email_lower)

        if result:
            logger.info(f"Invalidated cache for {email}")
        else:
            logger.debug(f"No cache entry to invalidate for {email}")

        return result

    def get_cache_health(self) -> dict:
        """Get cache health status."""
        if not self._platform_roles_cache:
            return {"cache_enabled": False, "cache_healthy": None}

        return {"cache_enabled": True, "cache_healthy": self._platform_roles_cache.health_check()}

    def get_all_users(self) -> Dict[str, List[str]]:
        """Get all users (for debugging/testing only)."""
        return self._user_roles_db.copy()

    def get_user_count(self) -> int:
        """Get count of users in database."""
        return len(self._user_roles_db)


