"""
API endpoints for Auth Kit FastAPI
"""

from .auth import router as auth_router
from .passkeys import router as passkeys_router
from .two_factor import router as two_factor_router

__all__ = [
    "auth_router",
    "passkeys_router", 
    "two_factor_router"
]