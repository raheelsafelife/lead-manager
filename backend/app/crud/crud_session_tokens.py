"""
CRUD operations for session tokens (secure authentication)
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from typing import Optional

from .. import models


def generate_secure_token() -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(32)


def create_session_token(db: Session, user_id: int, days_valid: int = 7) -> str:
    """
    Create a new session token for a user
    
    Args:
        db: Database session
        user_id: ID of the user
        days_valid: Number of days the token should be valid (default 7)
    
    Returns:
        The generated token string
    """
    # Generate unique token
    token = generate_secure_token()
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=days_valid)
    
    # Create token record
    db_token = models.SessionToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return token


def validate_token(db: Session, token: str) -> Optional[models.User]:
    """
    Validate a session token and return the associated user if valid
    
    Args:
        db: Database session
        token: The token string to validate
    
    Returns:
        User object if token is valid, None otherwise
    """
    # Find the token
    db_token = db.query(models.SessionToken).filter(
        models.SessionToken.token == token
    ).first()
    
    if not db_token:
        return None
    
    # Check if token has expired
    if db_token.expires_at < datetime.utcnow():
        # Delete expired token
        db.delete(db_token)
        db.commit()
        return None
    
    # Token is valid, return the user
    user = db.query(models.User).filter(
        models.User.id == db_token.user_id
    ).first()
    
    return user


def delete_user_tokens(db: Session, user_id: int):
    """
    Delete all session tokens for a user (logout from all devices)
    
    Args:
        db: Database session
        user_id: ID of the user
    """
    db.query(models.SessionToken).filter(
        models.SessionToken.user_id == user_id
    ).delete()
    db.commit()


def delete_token(db: Session, token: str):
    """
    Delete a specific session token (single device logout)
    
    Args:
        db: Database session
        token: The token string to delete
    """
    db.query(models.SessionToken).filter(
        models.SessionToken.token == token
    ).delete()
    db.commit()


def cleanup_expired_tokens(db: Session):
    """
    Delete all expired tokens from the database
    This should be called periodically (e.g., daily via cron/scheduler)
    
    Args:
        db: Database session
    """
    deleted_count = db.query(models.SessionToken).filter(
        models.SessionToken.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    
    return deleted_count
