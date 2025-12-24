import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SendGrid Configuration (preferred for production/Railway)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# SMTP Configuration (fallback for local development)
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # Default to 587 for TLS
SMTP_USERNAME = os.getenv("SENDER_EMAIL")
SMTP_PASSWORD = os.getenv("SENDER_PASSWORD")

# Try to import SendGrid (optional dependency)
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
    logger.info("SendGrid library loaded successfully")
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid library not available, will use SMTP fallback")


def send_email_via_sendgrid(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send email using SendGrid API (works on Railway)
    """
    try:
        if not SENDGRID_API_KEY or not SENDER_EMAIL:
            logger.error("SendGrid API key or sender email not configured")
            return False
        
        # Create SendGrid message
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body,
            html_content=html_body if html_body else body
        )
        
        # Send via SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✓ Email sent via SendGrid to {to_email} (status: {response.status_code})")
        return True
        
    except Exception as e:
        logger.error(f"✗ SendGrid error: {e}")
        return False


def send_email_via_smtp(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send email using SMTP (for local development)
    """
    try:
        # Get credentials from environment variables
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))  # Default to 587 for TLS
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        
        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            logger.error("Missing SMTP configuration in .env")
            logger.error(f"SMTP_SERVER: {smtp_server}, SMTP_PORT: {smtp_port}, SENDER_EMAIL: {sender_email}, SENDER_PASSWORD: {'***' if sender_password else 'None'}")
            return False
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email
        
        # Attach bodies
        part1 = MIMEText(body, "plain")
        msg.attach(part1)
        
        if html_body:
            part2 = MIMEText(html_body, "html")
            msg.attach(part2)
        
        # Connect and send based on port
        if smtp_port == 465:
            # Use SSL for port 465
            logger.info(f"Connecting to {smtp_server}:{smtp_port} using SSL")
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
        else:
            # Use TLS for port 587 (and other ports)
            logger.info(f"Connecting to {smtp_server}:{smtp_port} using STARTTLS")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()  # Identify ourselves to the server
                server.starttls()  # Secure the connection
                server.ehlo()  # Re-identify ourselves over TLS connection
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
            
        logger.info(f"✓ Email sent via SMTP to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"✗ SMTP Authentication failed: {e}")
        logger.error("Check your email and password. For Gmail, you may need an App Password if 2FA is enabled.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"✗ SMTP error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Failed to send email via SMTP: {e}")
        return False


def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send an email using SendGrid (preferred) or SMTP (fallback)
    - SendGrid: Works on Railway and production environments
    - SMTP: Works for local development
    """
    # Try SendGrid first if available and configured
    if SENDGRID_AVAILABLE and SENDGRID_API_KEY:
        logger.info("Attempting to send email via SendGrid...")
        result = send_email_via_sendgrid(to_email, subject, body, html_body)
        if result:
            return True
        logger.warning("SendGrid failed, falling back to SMTP...")
    
    # Fall back to SMTP
    logger.info("Attempting to send email via SMTP...")
    return send_email_via_smtp(to_email, subject, body, html_body)



def send_simple_lead_email(lead_info: dict, recipient_email: str) -> bool:
    """
    Send a simple automatic reminder email with basic lead information.
    Used for automatic 48-hour reminders.
    
    Args:
        lead_info: Dictionary with name, phone, creator, dob, source, status, created_date
        recipient_email: Email address to send reminder to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    name = lead_info.get('name', 'N/A')
    phone = lead_info.get('phone', 'N/A')
    creator = lead_info.get('creator', 'N/A')
    dob = lead_info.get('dob', 'N/A')
    source = lead_info.get('source', 'N/A')
    status = lead_info.get('status', 'N/A')
    created_date = lead_info.get('created_date', 'N/A')
    
    subject = f"🔔 Lead Reminder: {name}"
    
    # Plain text body
    body = f"""
Lead Follow-up Reminder

Name: {name}
Phone: {phone}
Date of Birth: {dob}

Source: {source}
Created By: {creator}
Created Date: {created_date}
Current Status: {status}

Please follow up with this lead.

This is an automatic reminder. You will continue to receive reminders every 48 hours until the lead becomes inactive or is marked as a referral.

Best regards,
Lead Manager System
    """
    
    # HTML Body
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">🔔 Lead Follow-up Reminder</h2>
            
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2980b9; margin-top: 0;">Lead Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Name:</td>
                        <td style="padding: 8px 0;">{name}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Phone:</td>
                        <td style="padding: 8px 0;">{phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Date of Birth:</td>
                        <td style="padding: 8px 0;">{dob}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #fff9e6; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #d68910; margin-top: 0;">Lead Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Source:</td>
                        <td style="padding: 8px 0;">{source}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Created By:</td>
                        <td style="padding: 8px 0;">{creator}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Created Date:</td>
                        <td style="padding: 8px 0;">{created_date}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Current Status:</td>
                        <td style="padding: 8px 0;"><span style="background-color: #3498db; color: white; padding: 5px 10px; border-radius: 5px;">{status}</span></td>
                    </tr>
                </table>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background-color: #e8f4f8; border-radius: 5px; border-left: 4px solid #3498db;">
                <p style="margin: 0; font-size: 14px;">⏰ Please follow up with this lead.</p>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border-radius: 5px; text-align: center;">
                <p style="margin: 0; font-size: 12px; color: #856404;">
                    <strong>Automatic Reminder:</strong> You will receive reminders every 48 hours until this lead becomes inactive or is marked as a referral.
                </p>
            </div>
            
            <p style="font-size: 12px; color: #777; text-align: center; margin-top: 20px;">
                Best regards,<br>
                <b>Lead Manager System</b>
            </p>
        </div>
      </body>
    </html>
    """
    
    return send_email(recipient_email, subject, body, html_body)


def send_referral_reminder_email(referral_info: dict, recipient_email: str) -> bool:
    """
    Send a referral-specific reminder email with comprehensive information.
    Used for automatic reminders based on referral type (Interim: 6hrs, Regular: 24hrs).
    
    Args:
        referral_info: Dictionary with name, phone, dob, creator, created_date, status,
                      referral_type, payor_name, payor_suboption, ccu_name, ccu_email, 
                      ccu_coordinator
        recipient_email: Email address to send reminder to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    name = referral_info.get('name', 'N/A')
    phone = referral_info.get('phone', 'N/A')
    dob = referral_info.get('dob', 'N/A')
    creator = referral_info.get('creator', 'N/A')
    created_date = referral_info.get('created_date', 'N/A')
    status = referral_info.get('status', 'N/A')
    referral_type = referral_info.get('referral_type', 'Regular')
    payor_name = referral_info.get('payor_name', 'N/A')
    payor_suboption = referral_info.get('payor_suboption', '')
    ccu_name = referral_info.get('ccu_name', 'N/A')
    ccu_email = referral_info.get('ccu_email', 'N/A')
    ccu_coordinator = referral_info.get('ccu_coordinator', 'N/A')
    
    # Build payor display with suboption if available
    payor_display = payor_name
    if payor_suboption:
        payor_display += f" - {payor_suboption}"
    
    subject = f"🏥 Referral Reminder [{referral_type}]: {name}"
    
    # Plain text body
    body = f"""
Referral Follow-up Reminder - {referral_type}

LEAD INFORMATION:
Name: {name}
Phone: {phone}
Date of Birth: {dob}

REFERRAL DETAILS:
Referral Type: {referral_type}
Current Status: {status}
Created By: {creator}
Created Date: {created_date}

PAYOR INFORMATION:
Payor: {payor_display}

CCU INFORMATION:
CCU Name: {ccu_name}
CCU Phone: {referral_info.get('ccu_phone', 'N/A')}
CCU Fax: {referral_info.get('ccu_fax', 'N/A')}
CCU Email: {ccu_email}
CCU Address: {referral_info.get('ccu_address', 'N/A')}
Supervisor/Coordinator: {ccu_coordinator}

Please follow up with this referral.

Reminder Schedule:
- All Referrals: Every 6 hours until Care Start

Best regards,
Lead Manager System
    """
    
    # HTML Body
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 650px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #e74c3c; padding-bottom: 10px;">
                🏥 Referral Follow-up Reminder
                <span style="background-color: #e74c3c; color: white; padding: 5px 12px; border-radius: 5px; font-size: 14px; margin-left: 10px;">{referral_type}</span>
            </h2>
            
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2980b9; margin-top: 0;">👤 Lead Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Name:</td>
                        <td style="padding: 8px 0;">{name}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Phone:</td>
                        <td style="padding: 8px 0;">{phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Date of Birth:</td>
                        <td style="padding: 8px 0;">{dob}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #fff3e6; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #d68910; margin-top: 0;">📋 Referral Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Referral Type:</td>
                        <td style="padding: 8px 0;"><span style="background-color: #e74c3c; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold;">{referral_type}</span></td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Current Status:</td>
                        <td style="padding: 8px 0;"><span style="background-color: #3498db; color: white; padding: 5px 10px; border-radius: 5px;">{status}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Created By:</td>
                        <td style="padding: 8px 0;">{creator}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Created Date:</td>
                        <td style="padding: 8px 0;">{created_date}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #e6f7ff; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">💼 Payor Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Payor:</td>
                        <td style="padding: 8px 0;">{payor_display}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #f0f9ff; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #52c41a;">
                <h3 style="color: #389e0d; margin-top: 0;">🏥 CCU Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">CCU Name:</td>
                        <td style="padding: 8px 0;">{ccu_name}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">CCU Phone:</td>
                        <td style="padding: 8px 0;">{referral_info.get('ccu_phone', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">CCU Fax:</td>
                        <td style="padding: 8px 0;">{referral_info.get('ccu_fax', 'N/A')}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">CCU Email:</td>
                        <td style="padding: 8px 0;">{ccu_email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">CCU Address:</td>
                        <td style="padding: 8px 0;">{referral_info.get('ccu_address', 'N/A')}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Supervisor/Coordinator:</td>
                        <td style="padding: 8px 0;">{ccu_coordinator}</td>
                    </tr>
                </table>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background-color: #fff2e8; border-radius: 5px; border-left: 4px solid #fa8c16;">
                <p style="margin: 0; font-size: 14px; font-weight: bold;">⏰ Please follow up with this referral.</p>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #f6ffed; border-radius: 5px; text-align: center;">
                <p style="margin: 0; font-size: 12px; color: #389e0d;">
                    <strong>Reminder Schedule:</strong><br>
                    <strong>All Referrals:</strong> Every 6 hours until Care Start
                </p>
            </div>
            
            <p style="font-size: 12px; color: #777; text-align: center; margin-top: 20px;">
                Best regards,<br>
                <b>Lead Manager System</b>
            </p>
        </div>
      </body>
    </html>
    """
    
    return send_email(recipient_email, subject, body, html_body)


def send_authorization_confirmation_email(auth_info: dict, recipient_email: str) -> bool:
    """
    Send an authorization confirmation email when authorization is marked as received.
    Emphasizes that authorization has been received and reminds about next steps.

    Args:
        auth_info: Dictionary with name, phone, creator, created_date, referral_type,
                  payor_name, auth_date
        recipient_email: Email address to send confirmation to

    Returns:
        bool: True if email sent successfully, False otherwise
    """

    name = auth_info.get('name', 'N/A')
    phone = auth_info.get('phone', 'N/A')
    creator = auth_info.get('creator', 'N/A')
    created_date = auth_info.get('created_date', 'N/A')
    referral_type = auth_info.get('referral_type', 'Regular')
    payor_name = auth_info.get('payor_name', 'N/A')
    auth_date = auth_info.get('auth_date', 'N/A')

    subject = f"✅ AUTHORIZATION CONFIRMED - {name} ({referral_type} Referral)"

    html_content = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Authorization Confirmed</title>
      </head>
      <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #52c41a; margin: 0;">✅ AUTHORIZATION CONFIRMED</h1>
                <p style="font-size: 16px; color: #666; margin: 5px 0;">This referral has received authorization</p>
            </div>

            <div style="background-color: #f6ffed; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #52c41a;">
                <h2 style="color: #389e0d; margin-top: 0;">📋 Referral Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; width: 40%;">Client Name:</td>
                        <td style="padding: 8px 0;">{name}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Phone:</td>
                        <td style="padding: 8px 0;">{phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Referral Type:</td>
                        <td style="padding: 8px 0;">{referral_type}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Payor:</td>
                        <td style="padding: 8px 0;">{payor_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold;">Created:</td>
                        <td style="padding: 8px 0;">{created_date}</td>
                    </tr>
                    <tr style="background-color: rgba(255,255,255,0.5);">
                        <td style="padding: 8px 0; font-weight: bold;">Created By:</td>
                        <td style="padding: 8px 0;">{creator}</td>
                    </tr>
                </table>
            </div>

            <div style="background-color: #fff2e8; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #fa8c16;">
                <h3 style="color: #fa8c16; margin-top: 0;">⏰ AUTHORIZATION RECEIVED</h3>
                <p style="margin: 10px 0; font-size: 16px;"><strong>Date & Time:</strong> {auth_date}</p>
                <p style="margin: 10px 0;">This referral has been authorized and is ready for care coordination.</p>
            </div>

            <div style="background-color: #e6f7ff; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #1890ff;">
                <h3 style="color: #1890ff; margin-top: 0;">🏥 NEXT STEPS</h3>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li><strong>Contact the client</strong> to schedule intake assessment</li>
                    <li><strong>Coordinate with CCU</strong> for care plan setup</li>
                    <li><strong>Mark as "Care Start"</strong> when services begin</li>
                    <li><strong>Update care status</strong> to "Care Start" or "Not Start"</li>
                </ul>
            </div>

            <div style="margin-top: 20px; padding: 15px; background-color: #fff7e6; border-radius: 5px; text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #d46b08;">
                    <strong>⚠️ Care Start Reminder:</strong><br>
                    <strong>Care Start Reminder:</strong> Every 6 hours until Care Start
                </p>
            </div>

            <p style="font-size: 12px; color: #777; text-align: center; margin-top: 20px;">
                Best regards,<br>
                <b>Lead Manager System</b>
            </p>
        </div>
      </body>
    </html>
    """

    try:
        # Debug logging
        print(f"[INFO] Attempting to send authorization email to {recipient_email}")
        print(f"[INFO] SMTP Config: Server={SMTP_SERVER}, Port={SMTP_PORT}, User={SMTP_USERNAME}")

        if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
            print("[ERROR] Missing SMTP configuration!")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email

        part = MIMEText(html_content, 'html')
        msg.attach(part)

        # Use appropriate SMTP method based on port
        if SMTP_PORT == 465:
            # Use SSL for port 465
            print(f"[INFO] Connecting using SSL on port {SMTP_PORT}")
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, msg.as_string())
            server.quit()
        else:
            # Use TLS for port 587 (and other ports)
            print(f"[INFO] Connecting using STARTTLS on port {SMTP_PORT}")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, msg.as_string())
            server.quit()

        print(f"[SUCCESS] Authorization confirmation email sent to {recipient_email} for {name}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] SMTP Authentication failed: {e}")
        print("[ERROR] Check your email and password. For Gmail, you may need an App Password if 2FA is enabled.")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to send authorization confirmation email to {recipient_email}: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_lead_reminder_email(lead_data: dict, recipient_email: str) -> bool:
    """
    Send a comprehensive reminder email for a lead with all details.
    Continues until lead becomes inactive or is marked as referral.
    
    Args:
        lead_data: Dictionary containing all lead information
        recipient_email: Email address to send reminder to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    # Extract lead information
    lead_id = lead_data.get('id')
    first_name = lead_data.get('first_name', '')
    last_name = lead_data.get('last_name', '')
    full_name = f"{first_name} {last_name}"
    phone = lead_data.get('phone', 'N/A')
    email = lead_data.get('email', 'N/A')
    city = lead_data.get('city', 'N/A')
    zip_code = lead_data.get('zip_code', 'N/A')
    dob = lead_data.get('dob', 'N/A')
    medicaid_no = lead_data.get('medicaid_no', 'N/A')
    
    # Source information
    source = lead_data.get('source', 'N/A')
    event_name = lead_data.get('event_name', '')
    word_of_mouth_type = lead_data.get('word_of_mouth_type', '')
    other_source_type = lead_data.get('other_source_type', '')
    
    # Staff and status
    staff_name = lead_data.get('staff_name', 'N/A')
    created_by = lead_data.get('created_by', 'N/A')
    contact_status = lead_data.get('last_contact_status', 'N/A')
    last_contact_date = lead_data.get('last_contact_date', 'N/A')
    
    # Referral information
    is_referral = lead_data.get('active_client', False)
    referral_type = lead_data.get('referral_type', 'N/A') if is_referral else 'Not a Referral'
    
    # Agency/Payor information
    agency_name = lead_data.get('agency_name', 'N/A')
    agency_suboption = lead_data.get('agency_suboption_name', '')
    
    # CCU information
    ccu_name = lead_data.get('ccu_name', 'N/A')
    ccu_address = lead_data.get('ccu_address', '')
    ccu_phone = lead_data.get('ccu_phone', '')
    ccu_fax = lead_data.get('ccu_fax', '')
    ccu_email = lead_data.get('ccu_email', '')
    ccu_coordinator = lead_data.get('ccu_coordinator', '')
    
    # Emergency contact
    e_contact_name = lead_data.get('e_contact_name', 'N/A')
    e_contact_relation = lead_data.get('e_contact_relation', 'N/A')
    e_contact_phone = lead_data.get('e_contact_phone', 'N/A')
    
    # Comments
    comments = lead_data.get('comments', 'None')
    
    subject = f"🔔 Lead Reminder: {full_name} - {contact_status}"
    
    # Build source details
    source_detail = source
    if event_name:
        source_detail += f" - {event_name}"
    elif word_of_mouth_type:
        source_detail += f" - {word_of_mouth_type}"
    elif other_source_type:
        source_detail += f" - {other_source_type}"
    
    # Build agency details
    agency_detail = agency_name
    if agency_suboption:
        agency_detail += f" ({agency_suboption})"
    
    # Plain text body
    body = f"""
Lead Follow-up Reminder
{'='*50}

LEAD INFORMATION:
------------------
Name: {full_name}
Lead ID: {lead_id}
Phone: {phone}
Email: {email}
City: {city}
ZIP Code: {zip_code}
Date of Birth: {dob}
Medicaid Number: {medicaid_no}

SOURCE INFORMATION:
-------------------
Source: {source_detail}
Created By: {created_by}
Assigned Staff: {staff_name}

CONTACT STATUS:
---------------
Current Status: {contact_status}
Last Contact Date: {last_contact_date}

REFERRAL INFORMATION:
---------------------
Is Referral: {'✅ Yes' if is_referral else '❌ No'}
Referral Type: {referral_type}
Agency/Payor: {agency_detail}

CCU INFORMATION:
----------------
CCU Name: {ccu_name}
{'Address: ' + ccu_address if ccu_address else ''}
{'Phone: ' + ccu_phone if ccu_phone else ''}
{'Fax: ' + ccu_fax if ccu_fax else ''}
{'Email: ' + ccu_email if ccu_email else ''}
{'Care Coordinator: ' + ccu_coordinator if ccu_coordinator else ''}

EMERGENCY CONTACT:
------------------
Name: {e_contact_name}
Relation: {e_contact_relation}
Phone: {e_contact_phone}

COMMENTS:
---------
{comments}

{'='*50}

Please log in to the Lead Manager to update this lead.

Best regards,
Lead Manager System
    """
    
    # HTML Body
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 700px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">🔔 Lead Follow-up Reminder</h2>
            
            <!-- Lead Information -->
            <h3 style="color: #2980b9; margin-top: 25px;">👤 Lead Information</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>Name</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{full_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Lead ID</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{lead_id}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Phone</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{phone}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Email</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{email}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>City</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{city}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>ZIP Code</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{zip_code}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Date of Birth</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{dob}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Medicaid Number</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{medicaid_no}</td>
                </tr>
            </table>
            
            <!-- Source Information -->
            <h3 style="color: #2980b9; margin-top: 25px;">📍 Source Information</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>Source</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{source_detail}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Created By</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{created_by}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Assigned Staff</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{staff_name}</td>
                </tr>
            </table>
            
            <!-- Contact Status -->
            <h3 style="color: #2980b9; margin-top: 25px;">📞 Contact Status</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>Current Status</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><span style="background-color: #3498db; color: white; padding: 5px 10px; border-radius: 5px;">{contact_status}</span></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Last Contact Date</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{last_contact_date}</td>
                </tr>
            </table>
            
            <!-- Referral Information -->
            <h3 style="color: #2980b9; margin-top: 25px;">🏥 Referral Information</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>Is Referral</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{'✅ Yes' if is_referral else '❌ No'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Referral Type</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{referral_type}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Agency/Payor</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{agency_detail}</td>
                </tr>
            </table>
            
            <!-- CCU Information -->
            {f'''
            <h3 style="color: #2980b9; margin-top: 25px;">🏥 CCU Information</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>CCU Name</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{ccu_name}</td>
                </tr>
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Address</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_address}</td></tr>" if ccu_address else ""}
                {f"<tr style='background-color: #f8f9fa;'><td style='padding: 10px; border: 1px solid #ddd;'><b>Phone</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_phone}</td></tr>" if ccu_phone else ""}
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Fax</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_fax}</td></tr>" if ccu_fax else ""}
                {f"<tr style='background-color: #f8f9fa;'><td style='padding: 10px; border: 1px solid #ddd;'><b>Email</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_email}</td></tr>" if ccu_email else ""}
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Care Coordinator</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_coordinator}</td></tr>" if ccu_coordinator else ""}
            </table>
            ''' if ccu_name != 'N/A' else ''}
            
            <!-- Emergency Contact -->
            <h3 style="color: #2980b9; margin-top: 25px;">🚨 Emergency Contact</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>Name</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{e_contact_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Relation</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{e_contact_relation}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Phone</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{e_contact_phone}</td>
                </tr>
            </table>
            
            {f'''
            <!-- Comments -->
            <h3 style="color: #2980b9; margin-top: 25px;">💬 Comments</h3>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 15px 0;">
                {comments}
            </div>
            ''' if comments and comments != 'None' else ''}
            
            <div style="margin-top: 30px; padding: 20px; background-color: #e8f4f8; border-radius: 5px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Please log in to the <b>Lead Manager</b> to update this lead.</p>
            </div>
            
            <br>
            <p style="font-size: 12px; color: #777; text-align: center; margin-top: 20px;">
                Best regards,<br>
                <b>Lead Manager System</b><br>
                <em>This reminder will continue until the lead becomes inactive or is marked as referral.</em>
            </p>
        </div>
      </body>
    </html>
    """
    
    return send_email(recipient_email, subject, body, html_body)


def send_referral_reminder(to_email: str, user_name: str, lead_name: str, lead_id: int, 
                           payor_name: str = None, payor_suboption: str = None, 
                           phone: str = None, source: str = None,
                           ccu_name: str = None, ccu_address: str = None, 
                           ccu_email: str = None, ccu_fax: str = None,
                           ccu_phone: str = None, ccu_coordinator: str = None) -> bool:
    """
    Send a specific reminder email for a referral follow-up with detailed info
    (Legacy function - use send_lead_reminder_email for comprehensive reminders)
    """
    subject = f"🔔 Reminder: Follow up with Referral {lead_name}"
    
    # Build payor display with suboption if available
    payor_display = payor_name or 'N/A'
    if payor_name and payor_suboption:
        payor_display = f"{payor_name} - {payor_suboption}"
    
    # Plain text body
    body = f"""
    Hi {user_name},
    
    This is a reminder to follow up with your new referral: {lead_name}.
    
    Lead Details:
    - ID: {lead_id}
    - Name: {lead_name}
    - Phone: {phone or 'N/A'}
    - Source: {source or 'N/A'}
    {f'- Payor: {payor_display}' if payor_name else ''}
    
    CCU Information:
    {f'- CCU Name: {ccu_name}' if ccu_name else '- CCU Name: N/A'}
    {f'- Address: {ccu_address}' if ccu_address else ''}
    {f'- Email: {ccu_email}' if ccu_email else ''}
    {f'- Fax: {ccu_fax}' if ccu_fax else ''}
    {f'- Phone: {ccu_phone}' if ccu_phone else ''}
    {f'- Contact Person: {ccu_coordinator}' if ccu_coordinator else ''}
    
    Please log in to the Lead Manager to view details and update the status.
    
    Best regards,
    Lead Manager System
    """
    
    # HTML Body
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #2c3e50;">🔔 Referral Follow-up Reminder</h2>
            <p>Hi <b>{user_name}</b>,</p>
            <p>This is a reminder to follow up with your new referral.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Lead Name</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{lead_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Lead ID</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{lead_id}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Phone</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{phone or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Source</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{source or 'N/A'}</td>
                </tr>
                {f'''
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Payor</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{payor_display}</td>
                </tr>
                ''' if payor_name else ''}
            </table>
            
            <!-- CCU Information Section -->
            <h3 style="color: #2980b9; margin-top: 25px;">🏥 CCU Information</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd; width: 40%;"><b>CCU Name</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{ccu_name or 'N/A'}</td>
                </tr>
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Address</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_address}</td></tr>" if ccu_address else ""}
                {f"<tr style='background-color: #f8f9fa;'><td style='padding: 10px; border: 1px solid #ddd;'><b>Email</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_email}</td></tr>" if ccu_email else ""}
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Fax</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_fax}</td></tr>" if ccu_fax else ""}
                {f"<tr style='background-color: #f8f9fa;'><td style='padding: 10px; border: 1px solid #ddd;'><b>Phone</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_phone}</td></tr>" if ccu_phone else ""}
                {f"<tr><td style='padding: 10px; border: 1px solid #ddd;'><b>Contact Person</b></td><td style='padding: 10px; border: 1px solid #ddd;'>{ccu_coordinator}</td></tr>" if ccu_coordinator else ""}
            </table>
            
            <p>Please log in to the Lead Manager to view details and update the status.</p>
            <br>
            <p style="font-size: 12px; color: #777;">Best regards,<br>Lead Manager System</p>
        </div>
      </body>
    </html>
    """
    
    return send_email(to_email, subject, body, html_body)
