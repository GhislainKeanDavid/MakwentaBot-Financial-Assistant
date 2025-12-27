"""
Password hashing and verification using bcrypt.

Provides secure password hashing with salt for user authentication.
Uses bcrypt algorithm with cost factor 12 for security.
"""

from passlib.context import CryptContext

# Configure password context with bcrypt
# Cost factor 12 provides good security/performance balance
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        password: Plain-text password string

    Returns:
        Bcrypt hashed password string

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed)
        $2b$12$... (60 character hash)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a hashed password.

    Args:
        plain_password: Plain-text password to verify
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Invalid hash format or other errors
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be updated.

    This is useful for upgrading to stronger hashing parameters over time.

    Args:
        hashed_password: The existing password hash

    Returns:
        True if hash should be updated, False otherwise
    """
    return pwd_context.needs_update(hashed_password)
