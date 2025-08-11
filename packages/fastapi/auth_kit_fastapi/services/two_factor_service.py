"""
Two-factor authentication service
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import pyotp
import qrcode
import io
import base64
import json
import secrets
import logging

from sqlalchemy.orm import Session

from ..models.user import BaseUser
from ..core.security import (
    generate_recovery_codes,
    hash_recovery_code,
    verify_recovery_code
)
from ..core.events import auth_events
from ..config import AuthConfig

logger = logging.getLogger(__name__)


class TwoFactorService:
    """
    Service for two-factor authentication operations
    
    Handles:
    - TOTP setup and verification
    - Recovery codes generation and validation
    - 2FA status management
    """
    
    def __init__(self, db: Session, config: AuthConfig):
        """
        Initialize 2FA service
        
        Args:
            db: Database session
            config: Authentication configuration
        """
        self.db = db
        self.config = config
        
    def get_2fa_status(
        self,
        user: BaseUser
    ) -> Dict[str, Any]:
        """
        Get 2FA status for user
        
        Args:
            user: User object
            
        Returns:
            2FA status information
        """
        recovery_codes_count = 0
        if user.two_factor_recovery_codes:
            try:
                recovery_codes = json.loads(user.two_factor_recovery_codes)
                recovery_codes_count = len([
                    c for c in recovery_codes 
                    if c.get("used") is False
                ])
            except Exception:
                pass
                
        return {
            "enabled": user.two_factor_enabled,
            "method": "totp" if user.two_factor_enabled else None,
            "backup_codes_remaining": recovery_codes_count if user.two_factor_enabled else None,
            "created_at": user.updated_at.isoformat() if user.two_factor_enabled else None
        }
        
    def generate_2fa_secret(self) -> str:
        """
        Generate new 2FA secret
        
        Returns:
            Base32 encoded secret
        """
        return pyotp.random_base32()
        
    def generate_qr_code(
        self,
        user: BaseUser,
        secret: str
    ) -> Tuple[str, str]:
        """
        Generate QR code for 2FA setup
        
        Args:
            user: User object
            secret: TOTP secret
            
        Returns:
            Tuple of (qr_code_data_url, provisioning_uri)
        """
        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.config.totp_issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=5
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_data_url = f"data:image/png;base64,{qr_code_b64}"
        
        return qr_code_data_url, provisioning_uri
        
    def verify_totp_code(
        self,
        secret: str,
        code: str
    ) -> bool:
        """
        Verify TOTP code
        
        Args:
            secret: TOTP secret
            code: User-provided code
            
        Returns:
            True if valid
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=self.config.totp_window)
        
    async def enable_2fa(
        self,
        user: BaseUser,
        secret: str,
        verification_code: str
    ) -> List[str]:
        """
        Enable 2FA for user
        
        Args:
            user: User object
            secret: TOTP secret
            verification_code: Verification code
            
        Returns:
            List of recovery codes
            
        Raises:
            ValueError: If verification fails or 2FA already enabled
        """
        # Check if already enabled
        if user.two_factor_enabled:
            raise ValueError("Two-factor authentication is already enabled")
            
        # Verify code
        if not self.verify_totp_code(secret, verification_code):
            raise ValueError("Invalid verification code")
            
        # Generate recovery codes
        recovery_codes = generate_recovery_codes(self.config.recovery_codes_count)
        
        # Hash recovery codes for storage
        hashed_codes = [
            {"code": hash_recovery_code(code), "used": False}
            for code in recovery_codes
        ]
        
        # Enable 2FA
        user.two_factor_enabled = True
        user.two_factor_secret = secret
        user.two_factor_recovery_codes = json.dumps(hashed_codes)
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Emit event
        await auth_events.emit("2fa_enabled", {
            "user_id": str(user.id)
        })
        
        return recovery_codes
        
    async def disable_2fa(
        self,
        user: BaseUser,
        password: str
    ) -> bool:
        """
        Disable 2FA for user
        
        Args:
            user: User object
            password: User password for verification
            
        Returns:
            True if disabled
            
        Raises:
            ValueError: If 2FA not enabled or password incorrect
        """
        # Check if enabled
        if not user.two_factor_enabled:
            raise ValueError("Two-factor authentication is not enabled")
            
        # Verify password
        if not user.verify_password(password):
            raise ValueError("Incorrect password")
            
        # Disable 2FA
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_recovery_codes = None
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Emit event
        await auth_events.emit("2fa_disabled", {
            "user_id": str(user.id)
        })
        
        return True
        
    async def regenerate_recovery_codes(
        self,
        user: BaseUser,
        password: str
    ) -> List[str]:
        """
        Regenerate recovery codes
        
        Args:
            user: User object
            password: User password for verification
            
        Returns:
            New recovery codes
            
        Raises:
            ValueError: If 2FA not enabled or password incorrect
        """
        # Check if 2FA enabled
        if not user.two_factor_enabled:
            raise ValueError("Two-factor authentication is not enabled")
            
        # Verify password
        if not user.verify_password(password):
            raise ValueError("Incorrect password")
            
        # Generate new recovery codes
        recovery_codes = generate_recovery_codes(self.config.recovery_codes_count)
        
        # Hash for storage
        hashed_codes = [
            {"code": hash_recovery_code(code), "used": False}
            for code in recovery_codes
        ]
        
        # Update recovery codes
        user.two_factor_recovery_codes = json.dumps(hashed_codes)
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Emit event
        await auth_events.emit("recovery_codes_generated", {
            "user_id": str(user.id)
        })
        
        return recovery_codes
        
    def verify_2fa_code(
        self,
        user: BaseUser,
        code: str,
        is_recovery_code: bool = False
    ) -> bool:
        """
        Verify 2FA code (TOTP or recovery)
        
        Args:
            user: User object
            code: Verification code
            is_recovery_code: Whether code is a recovery code
            
        Returns:
            True if valid
        """
        if not user.two_factor_enabled:
            return False
            
        if is_recovery_code:
            return self._verify_and_use_recovery_code(user, code)
        else:
            return self._verify_totp(user, code)
            
    def _verify_totp(
        self,
        user: BaseUser,
        code: str
    ) -> bool:
        """
        Verify TOTP code for user
        
        Args:
            user: User object
            code: TOTP code
            
        Returns:
            True if valid
        """
        if not user.two_factor_secret:
            return False
            
        return self.verify_totp_code(user.two_factor_secret, code)
        
    def _verify_and_use_recovery_code(
        self,
        user: BaseUser,
        code: str
    ) -> bool:
        """
        Verify and mark recovery code as used
        
        Args:
            user: User object
            code: Recovery code
            
        Returns:
            True if valid
        """
        if not user.two_factor_recovery_codes:
            return False
            
        try:
            recovery_codes = json.loads(user.two_factor_recovery_codes)
        except Exception:
            return False
            
        # Check each stored code
        for i, stored_code in enumerate(recovery_codes):
            if not stored_code.get("used", False):
                if verify_recovery_code(code, stored_code["code"]):
                    # Mark as used
                    recovery_codes[i]["used"] = True
                    user.two_factor_recovery_codes = json.dumps(recovery_codes)
                    self.db.commit()
                    return True
                    
        return False
        
    def get_remaining_recovery_codes(
        self,
        user: BaseUser
    ) -> int:
        """
        Get count of remaining recovery codes
        
        Args:
            user: User object
            
        Returns:
            Number of unused recovery codes
        """
        if not user.two_factor_recovery_codes:
            return 0
            
        try:
            recovery_codes = json.loads(user.two_factor_recovery_codes)
            return len([c for c in recovery_codes if not c.get("used", False)])
        except Exception:
            return 0
            
    async def handle_low_recovery_codes(
        self,
        user: BaseUser,
        threshold: int = 3
    ) -> bool:
        """
        Check and handle low recovery codes
        
        Args:
            user: User object
            threshold: Warning threshold
            
        Returns:
            True if below threshold
        """
        remaining = self.get_remaining_recovery_codes(user)
        
        if remaining <= threshold and remaining > 0:
            # Emit warning event
            await auth_events.emit("low_recovery_codes", {
                "user_id": str(user.id),
                "remaining_codes": remaining
            })
            return True
            
        return False