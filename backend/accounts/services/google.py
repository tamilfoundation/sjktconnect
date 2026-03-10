"""Google ID token verification."""

import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

_GOOGLE_CLIENT_IDS = None


def _get_client_ids():
    """Lazily load client IDs from settings."""
    global _GOOGLE_CLIENT_IDS
    if _GOOGLE_CLIENT_IDS is None:
        import os
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
        _GOOGLE_CLIENT_IDS = [client_id] if client_id else []
    return _GOOGLE_CLIENT_IDS


def verify_google_token(token: str) -> dict | None:
    """
    Verify a Google ID token and return user info.

    Returns dict with keys: sub, email, name, picture.
    Returns None if verification fails.
    """
    try:
        client_ids = _get_client_ids()
        if not client_ids:
            logger.error("GOOGLE_OAUTH_CLIENT_ID not configured")
            return None
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), clock_skew_in_seconds=10,
        )
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("Invalid issuer: %s", idinfo.get("iss"))
            return None
        if idinfo.get("aud") not in client_ids:
            logger.warning("Token audience mismatch")
            return None
        return {
            "sub": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except Exception:
        logger.exception("Google token verification failed")
        return None
