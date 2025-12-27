"""
Redis client for caching and session management.

Provides functions for JWT blacklisting, user session caching, and rate limiting.
Falls back gracefully if Redis is unavailable (logs warning but doesn't crash).
"""

import redis
import os
import json
from typing import Optional, Dict, Any

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Initialize Redis client
try:
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✓ Redis connected successfully")
except Exception as e:
    print(f"⚠ Redis connection failed: {e}")
    print("  Webapp will function without caching")
    redis_client = None
    REDIS_AVAILABLE = False


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get the Redis client instance.

    Returns:
        Redis client if available, None otherwise
    """
    return redis_client if REDIS_AVAILABLE else None


def blacklist_jwt(token: str, expiry_seconds: int) -> bool:
    """
    Add a JWT token to the blacklist (for logout).

    Args:
        token: The JWT token to blacklist
        expiry_seconds: How long to keep the token blacklisted (should match token expiry)

    Returns:
        True if successful, False if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        redis_client.setex(f"blacklist:{token}", expiry_seconds, "1")
        return True
    except Exception as e:
        print(f"Redis error in blacklist_jwt: {e}")
        return False


def is_jwt_blacklisted(token: str) -> bool:
    """
    Check if a JWT token is blacklisted.

    Args:
        token: The JWT token to check

    Returns:
        True if blacklisted, False otherwise (or if Redis unavailable)
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        return redis_client.exists(f"blacklist:{token}") > 0
    except Exception as e:
        print(f"Redis error in is_jwt_blacklisted: {e}")
        return False


def cache_user_session(user_id: int, session_data: Dict[str, Any], ttl: int = 3600) -> bool:
    """
    Cache user session data.

    Args:
        user_id: The user's ID
        session_data: Dictionary of session data to cache
        ttl: Time to live in seconds (default 1 hour)

    Returns:
        True if successful, False if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        redis_client.setex(
            f"session:{user_id}",
            ttl,
            json.dumps(session_data)
        )
        return True
    except Exception as e:
        print(f"Redis error in cache_user_session: {e}")
        return False


def get_cached_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached user session data.

    Args:
        user_id: The user's ID

    Returns:
        Session data dictionary if found, None otherwise
    """
    if not REDIS_AVAILABLE:
        return None

    try:
        data = redis_client.get(f"session:{user_id}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Redis error in get_cached_session: {e}")
        return None


def delete_cached_session(user_id: int) -> bool:
    """
    Delete cached user session data.

    Args:
        user_id: The user's ID

    Returns:
        True if successful, False if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        redis_client.delete(f"session:{user_id}")
        return True
    except Exception as e:
        print(f"Redis error in delete_cached_session: {e}")
        return False


def store_migration_code(code: str, telegram_user_id: str, ttl: int = 600) -> bool:
    """
    Store a Telegram-to-web migration verification code.

    Args:
        code: Verification code
        telegram_user_id: Telegram user ID
        ttl: Time to live in seconds (default 10 minutes)

    Returns:
        True if successful, False if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        redis_client.setex(f"migration_code:{code}", ttl, telegram_user_id)
        return True
    except Exception as e:
        print(f"Redis error in store_migration_code: {e}")
        return False


def get_migration_code(code: str) -> Optional[str]:
    """
    Retrieve Telegram user ID from migration code.

    Args:
        code: Verification code

    Returns:
        Telegram user ID if found, None otherwise
    """
    if not REDIS_AVAILABLE:
        return None

    try:
        return redis_client.get(f"migration_code:{code}")
    except Exception as e:
        print(f"Redis error in get_migration_code: {e}")
        return None


def delete_migration_code(code: str) -> bool:
    """
    Delete a migration code after successful verification.

    Args:
        code: Verification code

    Returns:
        True if successful, False if Redis unavailable
    """
    if not REDIS_AVAILABLE:
        return False

    try:
        redis_client.delete(f"migration_code:{code}")
        return True
    except Exception as e:
        print(f"Redis error in delete_migration_code: {e}")
        return False
