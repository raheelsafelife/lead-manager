
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.services.referral_report import generate_referral_report_excel
from app.db import SessionLocal

def test_excel_generation():
    print("Starting Excel generation test...")
    db = SessionLocal()
    try:
        excel_bytes = generate_referral_report_excel(db)
        print(f"Excel generated successfully. Size: {len(excel_bytes)} bytes")
        
        # Save to a local file for inspection if possible (not really possible here but let's see if it errors)
        with open("test_report.xlsx", "wb") as f:
            f.write(excel_bytes)
        print("Test file saved to test_report.xlsx")
        
    except Exception as e:
        print(f"Error during Excel generation: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_excel_generation()
