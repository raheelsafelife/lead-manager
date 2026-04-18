import base64
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from frontend_app.assets_base64 import LOGO_BASE64

# Extract the base64 part
header, encoded = LOGO_BASE64.split(",", 1)
data = base64.b64decode(encoded)

os.makedirs("scratch", exist_ok=True)
with open("scratch/check_logo.jpg", "wb") as f:
    f.write(data)

print("Saved logo to scratch/check_logo.jpg")
