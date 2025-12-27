"""
Authentication module for Financial Assistant webapp.

Provides JWT token management, password hashing, Google OAuth integration,
and FastAPI dependencies for user authentication.
"""

from .jwt import create_access_token, create_refresh_token, verify_token
from .password import hash_password, verify_password
from .oauth import google_oauth_callback
from .dependencies import get_current_user

__all__ = [
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'hash_password',
    'verify_password',
    'google_oauth_callback',
    'get_current_user',
]
