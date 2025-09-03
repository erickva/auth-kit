"""
Security utilities for JWT and password handling
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str]:
    """Create JWT refresh token with JTI"""
    to_encode = data.copy()
    jti = str(uuid4())
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "refresh"
    })
    
    token = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return token, jti


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError:
        raise ValueError("Invalid token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def generate_password_reset_token(email: str, secret_key: str) -> str:
    """Generate password reset token"""
    data = {
        "sub": email,
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(data, secret_key, algorithm="HS256")


def verify_password_reset_token(token: str, secret_key: str) -> Optional[str]:
    """Verify password reset token and return email"""
    try:
        payload = decode_token(token, secret_key)
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except Exception:
        return None


def generate_email_verification_token(email: str, secret_key: str) -> str:
    """Generate email verification token"""
    data = {
        "sub": email,
        "type": "email_verification",
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(data, secret_key, algorithm="HS256")


def verify_email_verification_token(token: str, secret_key: str) -> Optional[str]:
    """Verify email verification token and return email"""
    try:
        payload = decode_token(token, secret_key)
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except Exception:
        return None


def generate_recovery_codes(count: int = 10) -> List[str]:
    """Generate recovery codes for 2FA"""
    codes = []
    for _ in range(count):
        # Generate 16 character code in format XXXX-XXXX-XXXX-XXXX
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(16))
        formatted_code = '-'.join([code[i:i+4] for i in range(0, 16, 4)])
        codes.append(formatted_code)
    return codes


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage"""
    # Remove dashes for consistent hashing
    clean_code = code.replace('-', '')
    return pwd_context.hash(clean_code)


def verify_recovery_code(code: str, hashed_code: str) -> bool:
    """Verify a recovery code against hash"""
    clean_code = code.replace('-', '')
    return pwd_context.verify(clean_code, hashed_code)