"""
JWT Authentication Module for SanskritAI
Handles token creation, validation, and user extraction.
"""

import os
import time
import hmac
import hashlib
import base64
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone


# Token configuration
TOKEN_EXPIRY_HOURS = 24 * 7  # 7 days
TOKEN_SECRET_ENV = "AUTH_TOKEN_SECRET"


# In-memory revoked token store (in production, use Redis)
_REVOKED_TOKEN_DIGESTS: set = set()


def _get_token_secret() -> bytes:
    """Get the token signing secret."""
    configured_secret = os.getenv(TOKEN_SECRET_ENV)
    if configured_secret:
        return configured_secret.encode("utf-8")
    
    # In production, require explicit secret
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError(f"{TOKEN_SECRET_ENV} must be configured in production")
    
    # Development: use a persistent secret file
    secret_file = os.path.join(os.path.dirname(__file__), "..", "data", ".token_secret")
    os.makedirs(os.path.dirname(secret_file), exist_ok=True)
    
    if os.path.exists(secret_file):
        with open(secret_file, "rb") as f:
            return f.read()
    
    # Generate new secret for development
    secret = secrets.token_bytes(32)
    with open(secret_file, "wb") as f:
        f.write(secret)
    return secret


def create_access_token(username: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT-like access token using HMAC-SHA256.
    
    Format: base64url(payload).hex(signature)
    Payload: username:expiry_timestamp
    """
    secret = _get_token_secret()
    
    if expires_delta:
        expiry = datetime.now(timezone.utc) + expires_delta
    else:
        expiry = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    expiry_timestamp = int(expiry.timestamp())
    payload = f"{username}:{expiry_timestamp}".encode("utf-8")
    
    # Base64url encode payload (no padding)
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    
    # Create HMAC signature
    signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    
    return f"{encoded}.{signature}"


def verify_access_token(token: str) -> Optional[str]:
    """
    Verify an access token and return the username if valid.
    Returns None if token is invalid, expired, or revoked.
    """
    if not isinstance(token, str) or "." not in token:
        return None
    
    # Check if token is revoked
    if token_is_revoked(token):
        return None
    
    try:
        encoded, signature = token.split(".", 1)
    except ValueError:
        return None
    
    secret = _get_token_secret()
    
    # Verify signature
    expected_signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return None
    
    # Decode payload
    try:
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8")
        username, expiry_str = decoded.rsplit(":", 1)
        expiry = int(expiry_str)
    except (ValueError, UnicodeError, base64.binascii.Error):
        return None
    
    # Check expiry
    if expiry < int(time.time()):
        return None
    
    return username


def revoke_access_token(token: str) -> None:
    """Add token to revoked set."""
    if isinstance(token, str) and token:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        _REVOKED_TOKEN_DIGESTS.add(digest)


def token_is_revoked(token: str) -> bool:
    """Check if token is revoked."""
    if not isinstance(token, str):
        return True
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return digest in _REVOKED_TOKEN_DIGESTS