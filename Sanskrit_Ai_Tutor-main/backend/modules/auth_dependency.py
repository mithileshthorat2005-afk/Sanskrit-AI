"""
FastAPI Authentication Dependency
Provides get_current_user dependency for protected endpoints.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from modules.jwt_auth import verify_access_token, revoke_access_token
from modules.auth import Authenticator
from modules.sqlite_repository import SQLiteRepository


# Security scheme
security = HTTPBearer(auto_error=False)

# Global instances (initialized in main.py)
_authenticator: Optional[Authenticator] = None
_learning_db: Optional[SQLiteRepository] = None


def init_auth_dependencies(authenticator: Authenticator, learning_db: SQLiteRepository):
    """Initialize global dependencies."""
    global _authenticator, _learning_db
    _authenticator = authenticator
    _learning_db = learning_db


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    username = verify_access_token(token)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user details from authenticator
    if _authenticator and isinstance(_authenticator.users, dict) and username in _authenticator.users:
        user_data = _authenticator.users[username]
        # A hand-edited `users.json` record that is a string/list/number used to
        # raise AttributeError here, turning EVERY protected endpoint into a 500.
        # The token already proved identity, so fall back to defaults instead.
        if not isinstance(user_data, dict):
            user_data = {}
        return {
            "username": username,
            "role": user_data.get("role", "student"),
            "level": user_data.get("level", "beginner"),
            "completed": user_data.get("completed", 0)
        }
    
    # Fallback: check SQLite
    if _learning_db:
        user_id = _learning_db.get_user_id(username)
        if user_id:
            # Get role/level from SQLite
            with _learning_db.connect() as conn:
                row = conn.execute(
                    "SELECT role, level FROM users WHERE id = ?", (user_id,)
                ).fetchone()
                if row:
                    return {
                        "username": username,
                        "role": row["role"],
                        "level": row["level"],
                        "completed": 0
                    }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Optional authentication - returns None if not authenticated."""
    if not credentials:
        return None
    
    token = credentials.credentials
    username = verify_access_token(token)
    
    if not username:
        return None
    
    # Same logic as get_current_user but returns None instead of raising
    if _authenticator and isinstance(_authenticator.users, dict) and username in _authenticator.users:
        user_data = _authenticator.users[username]
        if not isinstance(user_data, dict):
            user_data = {}
        return {
            "username": username,
            "role": user_data.get("role", "student"),
            "level": user_data.get("level", "beginner"),
            "completed": user_data.get("completed", 0)
        }
    
    return None


def get_current_user_id(user: Dict[str, Any] = Depends(get_current_user)) -> int:
    """Get the SQLite user_id for the current user."""
    from modules.sqlite_repository import SQLiteRepository
    # We need to access the global learning_db
    global _learning_db
    if not _learning_db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    user_id = _learning_db.get_user_id(user["username"])
    if not user_id:
        # Create if doesn't exist
        user_data = {
            "username": user["username"],
            "role": user.get("role", "student"),
            "level": user.get("level", "beginner")
        }
        # We need to get the user data from authenticator or use defaults
        from modules.auth_dependency import _authenticator
        if (
            _authenticator
            and isinstance(_authenticator.users, dict)
            and user["username"] in _authenticator.users
        ):
            stored = _authenticator.users[user["username"]]
            # Non-dict record must not clobber the defaults built above —
            # `stored.get(...)` would raise AttributeError -> HTTP 500.
            if isinstance(stored, dict):
                user_data = stored
        user_id = _learning_db.ensure_user(
            user["username"],
            role=user_data.get("role", "student"),
            level=user_data.get("level", "beginner")
        )
    return user_id