from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional
import bcrypt

import app.models as models
from ..schemas import UserCreate
from ..utils.activity_logger import log_activity

# Use PBKDF2 as primary scheme for stability on Python 3.14/Windows
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# -------- Password Helpers --------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Check if this is a legacy bcrypt hash (starts with $2b$)
    if hashed_password and hashed_password.startswith("$2b$"):
        try:
            # This bypasses the buggy passlib bcrypt handler
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    # Otherwise use standard passlib (PBKDF2)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


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
        
        # Sync all related tables with the new username
        _sync_username_changes(db, old_username, new_username)
        
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


def delete_user(db: Session, user_id: int, admin_username: str, admin_id: int):
    """Delete an approved user with logging"""
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
        action_type="USER_DELETED",
        entity_type="User",
        entity_id=user_id,
        entity_name=username,
        description=f"User '{username}' deleted by admin",
        keywords="user,delete,admin"
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
    
    # Sync all related tables with the new username
    _sync_username_changes(db, old_username, new_username)
    
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



def admin_update_user_id(db: Session, user_id: int, new_user_id: str, admin_username: str, admin_id: int):
    """Admin updates a user's User ID (Employee ID) with logging"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    # Check if user_id already exists
    existing_user = get_user_by_user_id(db, new_user_id)
    if existing_user and existing_user.id != user_id:
        raise ValueError(f"User ID '{new_user_id}' is already assigned to {existing_user.username}")
    
    old_user_id = user.user_id
    user.user_id = new_user_id
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=admin_id,
        username=admin_username,
        action_type="USER_ID_UPDATED",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        description=f"User ID updated from '{old_user_id}' to '{new_user_id}' by admin",
        old_value={"user_id": old_user_id},
        new_value={"user_id": new_user_id},
        keywords="user,update,id"
    )
    
    return user
def admin_update_user(db: Session, user_id: int, username: str = None, password: str = None, admin_username: str = None, admin_id: int = None):
    """Deprecated wrapper for backward compatibility"""
    if username:
        admin_update_username(db, user_id, username, admin_username, admin_id)
    if password:
        admin_reset_password(db, user_id, password, admin_username, admin_id)


def _sync_username_changes(db: Session, old_username: str, new_username: str):
    """
    Internal helper to cascade username changes across all related tables.
    """
    if not old_username or not new_username or old_username == new_username:
        return

    # 1. Update Leads (staff_name, created_by, updated_by)
    db.query(models.Lead).filter(models.Lead.staff_name == old_username).update({models.Lead.staff_name: new_username}, synchronize_session=False)
    db.query(models.Lead).filter(models.Lead.created_by == old_username).update({models.Lead.created_by: new_username}, synchronize_session=False)
    db.query(models.Lead).filter(models.Lead.updated_by == old_username).update({models.Lead.updated_by: new_username}, synchronize_session=False)

    # 2. Update Events (created_by, updated_by)
    db.query(models.Event).filter(models.Event.created_by == old_username).update({models.Event.created_by: new_username}, synchronize_session=False)
    db.query(models.Event).filter(models.Event.updated_by == old_username).update({models.Event.updated_by: new_username}, synchronize_session=False)

    # 3. Update Agencies (created_by, updated_by)
    db.query(models.Agency).filter(models.Agency.created_by == old_username).update({models.Agency.created_by: new_username}, synchronize_session=False)
    db.query(models.Agency).filter(models.Agency.updated_by == old_username).update({models.Agency.updated_by: new_username}, synchronize_session=False)

    # 4. Update Agency Suboptions (created_by, updated_by)
    db.query(models.AgencySuboption).filter(models.AgencySuboption.created_by == old_username).update({models.AgencySuboption.created_by: new_username}, synchronize_session=False)
    db.query(models.AgencySuboption).filter(models.AgencySuboption.updated_by == old_username).update({models.AgencySuboption.updated_by: new_username}, synchronize_session=False)

    # 5. Update CCUs (created_by, updated_by)
    db.query(models.CCU).filter(models.CCU.created_by == old_username).update({models.CCU.created_by: new_username}, synchronize_session=False)
    db.query(models.CCU).filter(models.CCU.updated_by == old_username).update({models.CCU.updated_by: new_username}, synchronize_session=False)

    # 6. Update MCOs (created_by, updated_by)
    db.query(models.MCO).filter(models.MCO.created_by == old_username).update({models.MCO.created_by: new_username}, synchronize_session=False)
    db.query(models.MCO).filter(models.MCO.updated_by == old_username).update({models.MCO.updated_by: new_username}, synchronize_session=False)

    # 7. Update Activity Logs (username and entity_name)
    db.query(models.ActivityLog).filter(models.ActivityLog.username == old_username).update({models.ActivityLog.username: new_username}, synchronize_session=False)
    db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == "User",
        models.ActivityLog.entity_name == old_username
    ).update({models.ActivityLog.entity_name: new_username}, synchronize_session=False)
    
    # 8. Update Email Reminders (sent_by)
    db.query(models.EmailReminder).filter(models.EmailReminder.sent_by == old_username).update({models.EmailReminder.sent_by: new_username}, synchronize_session=False)

    db.flush() # Ensure changes are staged within the current transaction
