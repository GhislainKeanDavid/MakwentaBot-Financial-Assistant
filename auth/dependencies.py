"""
FastAPI authentication dependencies.

Provides dependency injection for authenticated routes.
Use get_current_user as a dependency to require authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Tuple, Optional
from .jwt import verify_token
import db_manager

# OAuth2 scheme for token extraction from Authorization header
# tokenUrl is the login endpoint that returns tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Tuple[int, str]:
    """
    FastAPI dependency that extracts and validates the current user from JWT token.

    Checks Authorization header for Bearer token, verifies it, and returns user info.

    Args:
        token: JWT token from Authorization header (injected by oauth2_scheme)

    Returns:
        Tuple of (user_id, email) for the authenticated user

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found

    Usage:
        @app.get("/api/protected")
        async def protected_route(current_user = Depends(get_current_user)):
            user_id, email = current_user
            return {"user_id": user_id, "email": email}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify and decode the token
    user_id = verify_token(token, token_type="access")

    if user_id is None:
        raise credentials_exception

    # Fetch user from database
    user = db_manager.get_user_by_id(user_id)

    if user is None:
        raise credentials_exception

    # Return user data (user_id, email)
    return user


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Tuple[int, str]]:
    """
    Optional authentication dependency.

    Returns user info if valid token is provided, None otherwise.
    Useful for routes that behave differently for authenticated vs anonymous users.

    Args:
        token: JWT token from Authorization header (optional)

    Returns:
        Tuple of (user_id, email) if authenticated, None otherwise

    Usage:
        @app.get("/api/data")
        async def get_data(current_user = Depends(get_current_user_optional)):
            if current_user:
                # Show personalized data
                return {"user_data": ...}
            else:
                # Show public data
                return {"public_data": ...}
    """
    if not token:
        return None

    try:
        user_id = verify_token(token, token_type="access")
        if user_id is None:
            return None

        user = db_manager.get_user_by_id(user_id)
        return user
    except Exception:
        return None
