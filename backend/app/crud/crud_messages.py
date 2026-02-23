"""
CRUD operations for messaging functionality
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import Message, User
from datetime import datetime


def send_message(db: Session, sender_id: int, receiver_id: int, content: str):
    """Send a message from one user to another"""
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        timestamp=datetime.utcnow(),
        is_read=False
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_chat_history(db: Session, user1_id: int, user2_id: int):
    """Get all messages between two users"""
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
        )
    ).order_by(Message.timestamp.asc()).all()
    return messages


def get_unread_count(db: Session, user_id: int):
    """Get count of unread messages for a user"""
    count = db.query(Message).filter(
        Message.receiver_id == user_id,
        Message.is_read == False
    ).count()
    return count


def mark_as_read(db: Session, current_user_id: int, other_user_id: int):
    """Mark all messages from other_user as read"""
    db.query(Message).filter(
        Message.sender_id == other_user_id,
        Message.receiver_id == current_user_id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()


def get_recent_conversations(db: Session, user_id: int):
    """Get list of recent conversations with unread counts"""
    from sqlalchemy import func, case
    
    # Subquery to get latest message timestamp for each conversation
    latest_messages = db.query(
        case(
            (Message.sender_id == user_id, Message.receiver_id),
            else_=Message.sender_id
        ).label('other_user_id'),
        func.max(Message.timestamp).label('last_timestamp')
    ).filter(
        or_(Message.sender_id == user_id, Message.receiver_id == user_id)
    ).group_by('other_user_id').subquery()
    
    # Get conversation details
    conversations = []
    for row in db.query(latest_messages).all():
        other_user = db.query(User).filter(User.id == row.other_user_id).first()
        if not other_user:
            continue
            
        # Get last message
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == row.other_user_id),
                and_(Message.sender_id == row.other_user_id, Message.receiver_id == user_id)
            )
        ).order_by(Message.timestamp.desc()).first()
        
        # Count unread
        unread = db.query(Message).filter(
            Message.sender_id == row.other_user_id,
            Message.receiver_id == user_id,
            Message.is_read == False
        ).count()
        
        conversations.append({
            'user_id': other_user.id,
            'username': other_user.username,
            'last_message': last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content,
            'last_timestamp': last_msg.timestamp,
            'unread_count': unread
        })
    
    # Sort by most recent
    conversations.sort(key=lambda x: x['last_timestamp'], reverse=True)
    return conversations
