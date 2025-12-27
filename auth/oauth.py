"""
Google OAuth 2.0 authentication integration.

Handles OAuth authorization code flow for Google Sign-In.
Requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI env vars.
"""

import httpx
import os
from typing import Dict, Optional

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Google OAuth endpoints
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleUserInfo:
    """Data class for Google user information."""

    def __init__(self, data: dict):
        self.id = data.get("id")
        self.email = data.get("email")
        self.verified_email = data.get("verified_email", False)
        self.name = data.get("name")
        self.given_name = data.get("given_name")
        self.family_name = data.get("family_name")
        self.picture = data.get("picture")
        self.locale = data.get("locale")


async def google_oauth_callback(code: str) -> Optional[GoogleUserInfo]:
    """
    Exchange authorization code for user information.

    This is step 2 of the OAuth flow - after user authorizes on Google,
    we exchange the code for an access token and fetch user info.

    Args:
        code: Authorization code from Google OAuth redirect

    Returns:
        GoogleUserInfo object with user details, or None on error

    Raises:
        httpx.HTTPError: If API requests fail
        ValueError: If required environment variables are missing
    """
    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
        raise ValueError(
            "Missing required Google OAuth environment variables: "
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI"
        )

    async with httpx.AsyncClient() as client:
        # Step 1: Exchange authorization code for access token
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if token_response.status_code != 200:
            print(f"Token exchange failed: {token_response.text}")
            return None

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            print("No access token in response")
            return None

        # Step 2: Use access token to fetch user information
        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_response.status_code != 200:
            print(f"Userinfo fetch failed: {user_response.text}")
            return None

        user_data = user_response.json()
        return GoogleUserInfo(user_data)


def get_google_auth_url() -> str:
    """
    Generate Google OAuth authorization URL.

    Returns:
        Full URL to redirect user to for Google Sign-In

    Example:
        https://accounts.google.com/o/oauth2/v2/auth?
        client_id=...&redirect_uri=...&response_type=code&scope=...
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI must be set")

    from urllib.parse import urlencode

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
