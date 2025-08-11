"""
Database management for Auth Kit
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Request

Base = declarative_base()


def get_db(request: Request) -> Generator[Session, None, None]:
    """
    Get database session from request state
    
    This function is designed to work with the session factory
    stored in app.state by create_auth_app()
    """
    SessionLocal = request.app.state.db_session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine) -> None:
    """
    Initialize database tables
    
    Args:
        engine: SQLAlchemy engine
    """
    # Import all models to ensure they're registered
    from ..models.user import BaseUser, UserCredential, UserSession
    
    # Create all tables
    Base.metadata.create_all(bind=engine)