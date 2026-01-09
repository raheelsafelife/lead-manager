import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app.utils.email_service import send_email

def test_dual_email():
    print("Testing Dual Email Reminders...")
    # This will use the environment variables from .env if present
    # We'll use a dummy recipient to check the logs/logic
    test_recipient = "test@example.com"
    subject = "Test Dual Reminder"
    body = "This is a test to verify BCC to admin."
    
    print(f"Triggering email to {test_recipient}...")
    success = send_email(test_recipient, subject, body)
    
    if success:
        print("Test trigger successful. Please check backend logs for BCC confirmation.")
    else:
        print("Test trigger failed. Check SMTP configuration.")

if __name__ == "__main__":
    test_dual_email()
