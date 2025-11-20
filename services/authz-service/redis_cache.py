"""
Redis caching layer for user roles.
Reduces database queries and improves performance.
"""

import redis
import json
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class PlatformRolesCache:
    """Redis-based cache for user platform roles"""
    
    def __init__(self, redis_url: str, ttl: int = 300):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://redis:6379)
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl
        logger.info(f"Redis cache initialized with TTL={ttl}s")
    
    def _make_key(self, email: str) -> str:
        """
        Generate cache key for user email.
        
        Format: user:platform-roles:{email}
        This prevents key collision with other services that may cache their own role data.
        """
        return f"user:platform-roles:{email.lower()}"
    
    def get_roles(self, email: str) -> Optional[List[str]]:
        """
        Get cached roles for a user.
        
        Args:
            email: User email address
        
        Returns:
            List of roles if found in cache, None if cache miss
        """
        key = self._make_key(email)
        try:
            cached = self.redis_client.get(key)
            if cached:
                roles = json.loads(cached)
                logger.info(f"Cache HIT for {email}")
                return roles
            else:
                logger.info(f"Cache MISS for {email}")
                return None
        except Exception as e:
            logger.error(f"Redis error on get for {email}: {e}")
            return None  # Fail gracefully - proceed without cache
    
    def set_roles(self, email: str, roles: List[str]) -> bool:
        """
        Cache roles for a user with TTL.
        
        Args:
            email: User email address
            roles: List of role names to cache
        
        Returns:
            True if successfully cached, False otherwise
        """
        key = self._make_key(email)
        try:
            value = json.dumps(roles)
            self.redis_client.setex(key, self.ttl, value)
            logger.info(f"Cached roles for {email} with TTL={self.ttl}s")
            return True
        except Exception as e:
            logger.error(f"Redis error on set for {email}: {e}")
            return False  # Fail gracefully
    
    def invalidate_roles(self, email: str) -> bool:
        """
        Remove cached roles for a user (useful for testing and admin operations).
        
        Args:
            email: User email address
        
        Returns:
            True if cache entry existed and was deleted, False otherwise
        """
        key = self._make_key(email)
        try:
            deleted = self.redis_client.delete(key)
            if deleted:
                logger.info(f"Invalidated cache for {email}")
                return True
            else:
                logger.info(f"No cache entry to invalidate for {email}")
                return False
        except Exception as e:
            logger.error(f"Redis error on invalidate for {email}: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        Check if Redis is accessible.
        
        Returns:
            True if Redis responds to PING, False otherwise
        """
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


def get_platform_roles_cache_instance() -> Optional[PlatformRolesCache]:
    """
    Get a cache instance if Redis is configured, otherwise return None.
    
    Returns:
        PlatformRolesCache instance if REDIS_URL is set, None otherwise
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.info("REDIS_URL not configured - caching disabled")
        return None
    
    try:
        redis_ttl = int(os.getenv("REDIS_TTL", "300"))
        cache = PlatformRolesCache(redis_url, redis_ttl)
        if cache.health_check():
            logger.info("Redis cache enabled and healthy")
            return cache
        else:
            logger.warning("Redis not healthy - caching disabled")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize Redis cache: {e}")
        return None
