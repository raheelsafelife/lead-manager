"""
Messages Page - Chat interface for user-to-user messaging
"""
import streamlit as st
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.crud import crud_users, crud_messages
from frontend.common import render_time


def view_messages():
    """Main messages page with conversation list and chat interface"""
    st.markdown('<div class="main-header">Messages</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    current_user_id = st.session_state.get('db_user_id')
    
    if not current_user_id:
        st.error("Session error: User ID not found. Please re-login.")
        db.close()
        return

    try:
        # Two column layout: conversation list | chat
        col_list, col_chat = st.columns([1, 2])
        
        with col_list:
            st.markdown("### Conversations")
            
            # Start New Chat
            with st.expander("➕ Start New Chat"):
                all_users = crud_users.get_approved_users(db)
                # Filter out current user
                other_users = [u for u in all_users if u.id != current_user_id]
                user_map = {u.username: u.id for u in other_users}
                
                sel_user = st.selectbox("Select user", ["Select User"] + list(user_map.keys()))
                if sel_user != "Select User":
                    if st.button("Open Chat", type="primary"):
                        st.session_state.active_chat_user_id = user_map[sel_user]
                        st.session_state.active_chat_username = sel_user
                        st.rerun()

            st.divider()
            
            # List existing conversations
            conversations = crud_messages.get_recent_conversations(db, current_user_id)
            
            if not conversations:
                st.info("No active conversations yet.")
            else:
                for conv in conversations:
                    # Styling for conversation item
                    is_active = st.session_state.get('active_chat_user_id') == conv['user_id']
                    bg_color = "#DFF8FF" if is_active else "transparent"
                    
                    # Unread badge
                    badge_html = f'<span style="background-color: #ef4444; color: white; border-radius: 50%; padding: 2px 6px; font-size: 0.7rem; margin-left: 5px;">{conv["unread_count"]}</span>' if conv['unread_count'] > 0 else ""
                    
                    item_html = f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 8px; cursor: pointer; border-bottom: 1px solid #f3f4f6;">
                        <div style="font-weight: bold; color: #00506b;">{conv['username']} {badge_html}</div>
                        <div style="font-size: 0.8rem; color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{conv['last_message']}</div>
                    </div>
                    """
                    st.markdown(item_html, unsafe_allow_html=True)
                    if st.button(f"Select {conv['username']}", key=f"sel_chat_{conv['user_id']}", use_container_width=True):
                        st.session_state.active_chat_user_id = conv['user_id']
                        st.session_state.active_chat_username = conv['username']
                        # Mark as read immediately when selected
                        crud_messages.mark_as_read(db, current_user_id, conv['user_id'])
                        st.rerun()

        with col_chat:
            active_id = st.session_state.get('active_chat_user_id')
            active_name = st.session_state.get('active_chat_username')
            
            if not active_id:
                st.markdown("""
                <div style="height: 400px; display: flex; align-items: center; justify-content: center; color: #9ca3af; border: 2px dashed #e5e7eb; border-radius: 12px;">
                    Select a conversation to start messaging
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"### Chat with {active_name}")
                st.divider()
                
                # Fetch history
                history = crud_messages.get_chat_history(db, current_user_id, active_id)
                
                # Chat bubble container
                chat_container = st.container(height=450)
                with chat_container:
                    if not history:
                        st.caption("No messages yet. Say hello!")
                    else:
                        for msg in history:
                            is_me = msg.sender_id == current_user_id
                            align = "right" if is_me else "left"
                            bg = "#00506b" if is_me else "#f3f4f6"
                            text_color = "white" if is_me else "#111827"
                            
                            bubble_html = f"""
                            <div style="display: flex; justify-content: {'flex-end' if is_me else 'flex-start'}; margin-bottom: 10px;">
                                <div style="max-width: 70%; background-color: {bg}; color: {text_color}; padding: 10px 15px; border-radius: 15px; border-bottom-{'right' if is_me else 'left'}-radius: 2px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                                    <div style="font-size: 0.95rem;">{msg.content}</div>
                                    <div style="font-size: 0.7rem; opacity: 0.7; text-align: right; margin-top: 5px;">{msg.timestamp.strftime('%I:%M %p')}</div>
                                </div>
                            </div>
                            """
                            st.markdown(bubble_html, unsafe_allow_html=True)

                # Send controls
                with st.form("send_message_form", clear_on_submit=True):
                    msg_text = st.text_area("Type your message...", key="new_msg_input", height=100)
                    col1, col2 = st.columns([4, 1])
                    with col2:
                        submit = st.form_submit_button("SEND", type="primary", use_container_width=True)
                        
                    if submit and msg_text.strip():
                        crud_messages.send_message(db, current_user_id, active_id, msg_text.strip())
                        st.rerun()

    finally:
        db.close()
