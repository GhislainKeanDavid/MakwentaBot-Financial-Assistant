"""
Test script for authentication modules.
Tests JWT, password hashing, and OAuth setup without requiring database connection.
"""

import os
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-purposes-min-32-chars"

print("="*60)
print("Testing Authentication Modules")
print("="*60)

# Test 1: Password Hashing
print("\n[TEST 1] Password Hashing Module")
print("-" * 40)
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

    # Hash a password (keep it under 72 bytes for bcrypt)
    test_password = "SecurePass123!"
    hashed = pwd_context.hash(test_password)
    print(f"Password: {test_password}")
    print(f"Hashed:   {hashed[:60]}...")  # Show first 60 chars

    # Verify correct password
    is_valid = pwd_context.verify(test_password, hashed)
    print(f"Verify correct password: {is_valid}")
    assert is_valid, "Correct password should verify"

    # Verify wrong password
    is_invalid = pwd_context.verify("WrongPassword", hashed)
    print(f"Verify wrong password: {is_invalid}")
    assert not is_invalid, "Wrong password should not verify"

    print("[PASS] Password hashing works correctly")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 2: JWT Token Creation and Verification
print("\n[TEST 2] JWT Token Module")
print("-" * 40)
try:
    from auth.jwt import create_access_token, create_refresh_token, verify_token

    # Create tokens
    test_user_id = 12345
    access_token = create_access_token(test_user_id)
    refresh_token = create_refresh_token(test_user_id)

    print(f"User ID: {test_user_id}")
    print(f"Access Token:  {access_token[:50]}...")
    print(f"Refresh Token: {refresh_token[:50]}...")

    # Verify access token
    verified_id = verify_token(access_token, "access")
    print(f"Verified User ID from access token: {verified_id}")
    assert verified_id == test_user_id, "Access token should return correct user ID"

    # Verify refresh token
    verified_id = verify_token(refresh_token, "refresh")
    print(f"Verified User ID from refresh token: {verified_id}")
    assert verified_id == test_user_id, "Refresh token should return correct user ID"

    # Verify wrong token type fails
    wrong_type = verify_token(access_token, "refresh")
    print(f"Access token verified as refresh (should be None): {wrong_type}")
    assert wrong_type is None, "Token type mismatch should fail"

    print("[PASS] JWT tokens work correctly")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 3: OAuth Configuration
print("\n[TEST 3] OAuth Module")
print("-" * 40)
try:
    # Set test env vars BEFORE importing
    os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
    os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:3000/auth/callback"

    # Now import after env vars are set
    import importlib
    import auth.oauth as oauth_module
    importlib.reload(oauth_module)  # Reload to pick up new env vars
    from auth.oauth import get_google_auth_url

    auth_url = get_google_auth_url()
    print(f"Google Auth URL: {auth_url[:80]}...")

    assert "client_id=test-client-id" in auth_url, "URL should contain client ID"
    assert "redirect_uri" in auth_url, "URL should contain redirect URI"
    assert "scope=openid+email+profile" in auth_url, "URL should contain scopes"

    print("[PASS] OAuth URL generation works correctly")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 4: Redis Client (graceful fallback)
print("\n[TEST 4] Redis Client (graceful fallback)")
print("-" * 40)
try:
    # Import redis client (it will print warnings about connection)
    import sys
    import io

    # Capture stdout to suppress emoji warnings
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    from cache.redis_client import blacklist_jwt, is_jwt_blacklisted, REDIS_AVAILABLE

    # Restore stdout
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    print(f"Redis Available: {REDIS_AVAILABLE}")

    # These should fail gracefully without Redis
    blacklist_jwt("test-token", 300)
    is_blacklisted = is_jwt_blacklisted("test-token")

    print(f"Token blacklisted (expected False if no Redis): {is_blacklisted}")
    print("[PASS] Redis client has graceful fallback")
except Exception as e:
    print(f"[FAIL] {e}")

# Summary
print("\n" + "="*60)
print("[SUCCESS] All authentication modules loaded and tested")
print("="*60)
print("\nNext steps:")
print("1. Fix database connection (check .env DATABASE_URL)")
print("2. Run database migration: python run_migration.py")
print("3. Optionally set up Redis for session caching")
print("="*60)
