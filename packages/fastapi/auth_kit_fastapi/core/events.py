"""
Event system for authentication events
"""

from typing import Dict, List, Callable, Any, Coroutine
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class AuthEventEmitter:
    """
    Event emitter for authentication events
    
    Supports both sync and async event handlers
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        
    def on(self, event: str, handler: Callable) -> Callable:
        """
        Register an event handler
        
        Args:
            event: Event name
            handler: Event handler function (sync or async)
            
        Returns:
            The handler function (for use as decorator)
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        return handler
        
    def off(self, event: str, handler: Callable) -> None:
        """
        Unregister an event handler
        
        Args:
            event: Event name
            handler: Event handler to remove
        """
        if event in self._handlers:
            self._handlers[event].remove(handler)
            
    async def emit(self, event: str, data: Any = None) -> None:
        """
        Emit an event
        
        Args:
            event: Event name
            data: Event data
        """
        if event not in self._handlers:
            return
            
        # Create event object
        event_obj = {
            "type": event,
            "timestamp": datetime.utcnow(),
            "data": data
        }
        
        # Call all handlers
        for handler in self._handlers[event]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_obj)
                else:
                    # Run sync handler in thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        None, handler, event_obj
                    )
            except Exception as e:
                logger.error(f"Error in auth event handler for {event}: {e}")
                
    def emit_sync(self, event: str, data: Any = None) -> None:
        """
        Emit an event synchronously (for use in sync contexts)
        
        Args:
            event: Event name
            data: Event data
        """
        # Create a new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(self.emit(event, data))


# Global event emitter instance
auth_events = AuthEventEmitter()


# Predefined events
AUTH_EVENTS = {
    # User events
    "user_registered": "User registered",
    "user_logged_in": "User logged in",
    "user_logged_out": "User logged out",
    "user_updated": "User profile updated",
    "user_deleted": "User deleted",
    
    # Authentication events
    "password_changed": "Password changed",
    "password_reset_requested": "Password reset requested",
    "password_reset_completed": "Password reset completed",
    "email_verified": "Email verified",
    "email_verification_sent": "Email verification sent",
    
    # 2FA events
    "2fa_enabled": "Two-factor authentication enabled",
    "2fa_disabled": "Two-factor authentication disabled",
    "2fa_verified": "Two-factor authentication verified",
    "recovery_codes_generated": "Recovery codes generated",
    
    # Passkey events
    "passkey_registered": "Passkey registered",
    "passkey_authenticated": "Passkey authenticated",
    "passkey_deleted": "Passkey deleted",
    
    # Security events
    "suspicious_login_attempt": "Suspicious login attempt",
    "account_locked": "Account locked",
    "account_unlocked": "Account unlocked",
    "session_expired": "Session expired",
    "token_refreshed": "Token refreshed"
}