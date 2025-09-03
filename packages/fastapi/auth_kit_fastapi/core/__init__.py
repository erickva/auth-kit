"""
Core authentication modules for Auth Kit FastAPI
"""

from .app import create_auth_app
from .config import AuthConfig
from .database import get_db, init_db
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_verified_user,
    require_superuser
)
from .events import auth_events
from .security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token
)

__all__ = [
    "create_auth_app",
    "AuthConfig",
    "get_db",
    "init_db",
    "get_current_user",
    "get_current_active_user",
    "require_verified_user",
    "require_superuser",
    "auth_events",
    "create_access_token",
    "create_refresh_token",
    "verify_password",
    "get_password_hash",
    "decode_token"
]