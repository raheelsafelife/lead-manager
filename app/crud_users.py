from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional

from . import models
from .schemas import UserCreate
from .utils.activity_logger import log_activity

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------- Password Helpers --------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# -------- CRUD Operations --------
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_user_id(db: Session, user_id: str):
    """Get user by unique user_id"""
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def create_user(db: Session, user_in: UserCreate, performer_username: str = "System", performer_id: Optional[int] = None):
    """Create a new user with logging"""
    hashed_pw = hash_password(user_in.password)

    user = models.User(
        user_id=user_in.user_id,
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=performer_id,
        username=performer_username,
        action_type="USER_CREATED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"User '{user.username}' created",
        new_value={"username": user.username, "role": user.role, "email": user.email},
        keywords="user,create"
    )
    
    return user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None
    
    # Check if user is approved
    if not user.is_approved:
        return "pending"  # Special return value for pending approval

    return user


def update_user_credentials(
    db: Session,
    user_id: int,
    new_username: str = None,
    new_password: str = None,
    performer_username: str = None,
    performer_id: int = None
):
    """
    Update user's username and/or password with logging.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        return None
    
    old_username = user.username
    changes = {}
    
    # Update username if provided
    if new_username is not None:
        # Check if username already exists
        existing_user = get_user_by_username(db, new_username)
        if existing_user and existing_user.id != user_id:
            raise ValueError(f"Username '{new_username}' is already taken")
        user.username = new_username
        changes["username"] = {"old": old_username, "new": new_username}
    
    # Update password if provided
    if new_password is not None:
        user.hashed_password = hash_password(new_password)
        changes["password"] = {"old": "***", "new": "***"}
    
    db.commit()
    db.refresh(user)
    
    # Log activity
    if changes:
        description = "User credentials updated"
        if "password" in changes and "username" in changes:
            description = "Username and password updated"
        elif "password" in changes:
            description = "Password updated"
        elif "username" in changes:
            description = f"Username updated from '{old_username}' to '{new_username}'"
            
        log_activity(
            db=db,
            user_id=performer_id or user.id,
            username=performer_username or user.username,
            action_type="PASSWORD_CHANGED" if "password" in changes else "USER_UPDATED",
            entity_type="User",
            entity_id=user.id,
            entity_name=user.username,
            description=description,
            keywords="user,update,security"
        )
        
    return user


# -------- Approval Workflow --------
def get_pending_users(db: Session):
    """Get all users pending approval"""
    return db.query(models.User).filter(models.User.is_approved == False).all()


def get_approved_users(db: Session):
    """Get all approved users"""
    return db.query(models.User).filter(models.User.is_approved == True).all()


def approve_user(db: Session, user_id: int, admin_username: str, admin_id: int):
    """Approve a user by ID with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    user.is_approved = True
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_APPROVED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"User '{user.username}' approved",
        keywords="user,approve"
    )
    
    return user


def reject_user(db: Session, user_id: int, admin_username: str, admin_id: int):
    """Reject and delete a pending user with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    username = user.username
    db.delete(user)
    db.commit()
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_REJECTED",
        entity_type="User",
        entity_id=user_id,
        entity_name=username,
        description=f"User '{username}' rejected and deleted",
        keywords="user,reject"
    )
    
    return True


def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_all_users(db: Session):
    """Get all users"""
    return db.query(models.User).order_by(models.User.username).all()


# -------- Password Reset Workflow --------
def request_password_reset(db: Session, username: str):
    """Mark user as requesting password reset"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    user.password_reset_requested = True
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        action_type="PASSWORD_RESET_REQUESTED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Password reset requested for '{user.username}'",
        keywords="user,security,reset"
    )
    
    return user


def get_password_reset_requests(db: Session):
    """Get all users who have requested password reset"""
    return db.query(models.User).filter(models.User.password_reset_requested == True).all()


def admin_reset_password(db: Session, user_id: int, new_password: str, admin_username: str, admin_id: int):
    """Admin resets a user's password and clears reset request with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    user.hashed_password = hash_password(new_password)
    user.password_reset_requested = False
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="PASSWORD_RESET_COMPLETED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Password reset for '{user.username}' by admin",
        keywords="user,security,reset"
    )
    
    return user


# -------- Admin User Management --------
def update_user_role(db: Session, user_id: int, new_role: str, admin_username: str, admin_id: int):
    """Update user's role with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    if new_role not in ["user", "admin"]:
        raise ValueError(f"Invalid role: {new_role}. Must be 'user' or 'admin'")
    
    old_role = user.role
    user.role = new_role
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_ROLE_UPDATED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Role updated from '{old_role}' to '{new_role}' for '{user.username}'",
        old_value={"role": old_role},
        new_value={"role": new_role},
        keywords="user,role,update"
    )
    
    return user


def admin_update_username(db: Session, user_id: int, new_username: str, admin_username: str, admin_id: int):
    """Admin updates a user's username with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    # Check if username already exists
    existing_user = get_user_by_username(db, new_username)
    if existing_user and existing_user.id != user_id:
        raise ValueError(f"Username '{new_username}' is already taken")
    
    old_username = user.username
    user.username = new_username
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_USERNAME_UPDATED",
        entity_type="User",
        entity_id=user.id,
        entity_name=new_username,
        description=f"Username updated from '{old_username}' to '{new_username}' by admin",
        old_value={"username": old_username},
        new_value={"username": new_username},
        keywords="user,update"
    )
    
    return user


def admin_update_email(db: Session, user_id: int, new_email: str, admin_username: str, admin_id: int):
    """Admin updates a user's email with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    # Check if email already exists
    existing_user = get_user_by_email(db, new_email)
    if existing_user and existing_user.id != user_id:
        raise ValueError(f"Email '{new_email}' is already registered")
    
    old_email = user.email
    user.email = new_email
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_EMAIL_UPDATED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Email updated from '{old_email}' to '{new_email}' by admin",
        old_value={"email": old_email},
        new_value={"email": new_email},
        keywords="user,update,email"
    )
    
    return user



def admin_update_user(db: Session, user_id: int, username: str = None, password: str = None, admin_username: str = None, admin_id: int = None):
    """Deprecated wrapper for backward compatibility"""
    if username:
        admin_update_username(db, user_id, username, admin_username, admin_id)
    if password:
        admin_reset_password(db, user_id, password, admin_username, admin_id)
