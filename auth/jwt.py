"""
JWT token management for authentication.

Provides functions to create and verify access and refresh tokens.
Uses JOSE (JavaScript Object Signing and Encryption) for JWT handling.
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "development-secret-key-min-32-chars-long-please-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: int) -> str:
    """
    Create a short-lived access token for API authentication.

    Args:
        user_id: The user's database ID

    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a long-lived refresh token for obtaining new access tokens.

    Args:
        user_id: The user's database ID

    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[int]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type matches expected type
        if payload.get("type") != token_type:
            return None

        # Extract and return user ID
        user_id = payload.get("sub")
        if user_id is None:
            return None

        return int(user_id)

    except JWTError:
        # Token is invalid, expired, or malformed
        return None
    except ValueError:
        # user_id is not a valid integer
        return None


def get_token_expiry(token: str) -> Optional[int]:
    """
    Get the expiration time remaining for a token.

    Args:
        token: The JWT token string

    Returns:
        Seconds until expiration, or None if token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp is None:
            return None

        now = datetime.utcnow().timestamp()
        expiry = exp - now

        return int(max(0, expiry))

    except JWTError:
        return None
