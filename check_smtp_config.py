"""
Railway SMTP Diagnostic Script
Run this to check if your SMTP configuration is correct on Railway
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("RAILWAY SMTP CONFIGURATION CHECK")
print("=" * 60)

# Check environment variables
print("\n1. ENVIRONMENT VARIABLES:")
print("-" * 60)

sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = os.getenv("SMTP_PORT")
sendgrid_key = os.getenv("SENDGRID_API_KEY")

print(f"SENDER_EMAIL:      {'[OK] SET' if sender_email else '[X] MISSING'} {f'({sender_email})' if sender_email else ''}")
print(f"SENDER_PASSWORD:   {'[OK] SET' if sender_password else '[X] MISSING'} {'(***hidden***)' if sender_password else ''}")
print(f"SMTP_SERVER:       {'[OK] SET' if smtp_server else '[X] MISSING'} {f'({smtp_server})' if smtp_server else ''}")
print(f"SMTP_PORT:         {'[OK] SET' if smtp_port else '[X] MISSING (will use 587)'} {f'({smtp_port})' if smtp_port else ''}")
print(f"SENDGRID_API_KEY:  {'[OK] SET' if sendgrid_key else '[X] NOT SET'} {'(***hidden***)' if sendgrid_key else ''}")

# Check if SMTP is properly configured
print("\n2. SMTP CONFIGURATION STATUS:")
print("-" * 60)

if sender_email and sender_password and smtp_server:
    print("[OK] SMTP is configured and should work")
    print(f"  Will connect to: {smtp_server}:{smtp_port or 587}")
else:
    print("[X] SMTP is NOT properly configured")
    print("  Missing required variables:")
    if not sender_email:
        print("    - SENDER_EMAIL")
    if not sender_password:
        print("    - SENDER_PASSWORD")
    if not smtp_server:
        print("    - SMTP_SERVER")

# Check SendGrid
print("\n3. SENDGRID STATUS:")
print("-" * 60)
if sendgrid_key:
    print("[OK] SendGrid API key is configured")
    print("  Emails will use SendGrid (recommended for Railway)")
else:
    print("[X] SendGrid is not configured")
    print("  Will fall back to SMTP")

# Recommendations
print("\n4. RECOMMENDATIONS:")
print("-" * 60)

if not sender_email or not sender_password or not smtp_server:
    print("[!] ACTION REQUIRED:")
    print("   Go to Railway -> Your Service -> Variables")
    print("   Add the following variables:")
    print("")
    if not sender_email:
        print("   SENDER_EMAIL=your-email@gmail.com")
    if not sender_password:
        print("   SENDER_PASSWORD=your-gmail-app-password")
    if not smtp_server:
        print("   SMTP_SERVER=smtp.gmail.com")
    if not smtp_port:
        print("   SMTP_PORT=587")
else:
    print("[OK] All SMTP variables are set!")
    print("  If emails still don't work, check:")
    print("  1. Gmail App Password is correct")
    print("  2. Railway logs for specific error messages")
    print("  3. Consider using SendGrid for better reliability")

print("\n" + "=" * 60)
