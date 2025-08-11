"""
Test configuration and fixtures
"""

import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from auth_kit_fastapi import AuthConfig, init_auth
from auth_kit_fastapi.models import Base, BaseUser
from auth_kit_fastapi.core.database import get_db


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Auth configuration for tests
@pytest.fixture
def auth_config():
    """Test auth configuration"""
    return AuthConfig(
        jwt_secret="test-secret-key",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        passkey_rp_id="localhost",
        passkey_rp_name="Test App",
        passkey_origin="http://localhost",
        passkey_timeout_ms=60000,
        totp_issuer="Test App",
        totp_window=1,
        recovery_codes_count=8,
        app_name="Test App",
        app_url="http://localhost",
        features={
            "email_verification": True,
            "password_reset": True,
            "two_factor": True,
            "passkeys": True
        }
    )


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app(auth_config, db):
    """Test FastAPI application"""
    from fastapi import FastAPI
    from auth_kit_fastapi import auth_router
    
    app = FastAPI()
    
    # Override database dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Initialize auth
    init_auth(app, auth_config, TestingSessionLocal)
    app.include_router(auth_router, prefix="/api")
    
    return app


@pytest.fixture
def client(app):
    """Test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db) -> BaseUser:
    """Create a test user"""
    user = BaseUser(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    user.set_password("password123")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@pytest.fixture
def test_user_unverified(db) -> BaseUser:
    """Create an unverified test user"""
    user = BaseUser(
        email="unverified@example.com",
        first_name="Unverified",
        last_name="User",
        is_active=True,
        is_verified=False
    )
    user.set_password("password123")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@pytest.fixture
def test_user_with_2fa(db) -> BaseUser:
    """Create a test user with 2FA enabled"""
    user = BaseUser(
        email="2fa@example.com",
        first_name="2FA",
        last_name="User",
        is_active=True,
        is_verified=True,
        two_factor_enabled=True,
        two_factor_secret="JBSWY3DPEHPK3PXP"  # Test secret
    )
    user.set_password("password123")
    
    # Add recovery codes
    import json
    from auth_kit_fastapi.core.security import hash_recovery_code
    
    recovery_codes = ["AAAA-BBBB", "CCCC-DDDD", "EEEE-FFFF"]
    hashed_codes = [
        {"code": hash_recovery_code(code), "used": False}
        for code in recovery_codes
    ]
    user.two_factor_recovery_codes = json.dumps(hashed_codes)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get auth headers for test user"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    return {
        "Authorization": f"Bearer {data['tokens']['access_token']}"
    }


@pytest.fixture
def auth_headers_2fa(client, test_user_with_2fa):
    """Get auth headers for 2FA user (temp token)"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user_with_2fa.email,
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_2fa"] is True
    
    return {
        "Authorization": f"Bearer {data['tokens']['access_token']}"
    }