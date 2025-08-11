"""
Auth Kit FastAPI - Complete authentication solution for FastAPI applications
"""

from .core.config import AuthConfig
from .core.app import create_auth_app
from .core.dependencies import (
    get_current_user,
    get_current_active_user,
    require_verified_user,
    require_superuser
)
from .models.user import BaseUser
from .core.events import auth_events

__version__ = "1.0.0"

__all__ = [
    "AuthConfig",
    "create_auth_app",
    "get_current_user",
    "get_current_active_user", 
    "require_verified_user",
    "require_superuser",
    "BaseUser",
    "auth_events"
]