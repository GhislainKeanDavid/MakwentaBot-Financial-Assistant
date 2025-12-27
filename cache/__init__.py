"""
Caching module using Redis.

Provides functions for session caching, JWT blacklisting, and rate limiting.
"""

from .redis_client import (
    get_redis_client,
    blacklist_jwt,
    is_jwt_blacklisted,
    cache_user_session,
    get_cached_session,
    delete_cached_session
)

__all__ = [
    'get_redis_client',
    'blacklist_jwt',
    'is_jwt_blacklisted',
    'cache_user_session',
    'get_cached_session',
    'delete_cached_session',
]
