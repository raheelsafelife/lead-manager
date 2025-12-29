"""
FastAPI Microservice for SafeLife CCP Form Integration
Provides REST API endpoint to receive leads from external form
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from app.db import SessionLocal
from app.crud import crud_leads, crud_users
from app.schemas import LeadCreate
import os

app = FastAPI(title="Lead Manager API", version="1.0.0")

# CORS configuration for Netlify/External Form
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: specify ["https://your-form.netlify.app", "http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key for authentication (store in .env)
API_KEY = os.getenv("LEAD_MANAGER_API_KEY", "your-secret-api-key-here")


class SafeLifeFormData(BaseModel):
    """Schema for SafeLife CCP Form submissions"""
    # User identification
    staff_name: str = Field(..., description="Staff member name")
    user_id: str = Field(..., description="Staff member User ID")
    
    # Client information
    name: str = Field(..., description="Client's full name")
    relation: str = Field(..., description="Relation of form submitter to client")
    
    # Birth information
    birthdate: Optional[str] = Field(None, description="Birthdate in mm/dd/yyyy format")
    age: Optional[str] = Field(None, description="Client's age if birthdate unknown")
    
    # Medicaid
    medicaid: str = Field(..., description="yes or no")
    medicaid_number: Optional[str] = Field(None, description="Medicaid number if known")
    
    # Contact
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    
    # Address
    address_line1: Optional[str] = Field(None)
    address_line2: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    zip: Optional[str] = Field(None)
    county: Optional[str] = Field(None)
    
    # Source & Priority
    source: str = Field(..., description="Lead source")
    priority: Optional[str] = Field("Medium", description="Lead priority (High, Medium, Low)")

    # SOC Date (for Transfer source)
    soc_date: Optional[str] = Field(None, description="Start of Care date in mm/dd/yyyy or yyyy-mm-dd format")

    # Additional info
    info: Optional[str] = Field(None, description="Additional information")


def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key for authentication"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.post("/api/external-lead")
async def create_external_lead(
    form_data: SafeLifeFormData
):
    """
    Receive lead submission from SafeLife CCP Form
    
    - Validates user_id against database
    - Maps form fields to Lead schema
    - Creates lead in database
    """
    # Authorization removed per request
    
    db = SessionLocal()
    
    try:
        # 1. Verify user_id exists
        user = crud_users.get_user_by_user_id(db, form_data.user_id)
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"User ID '{form_data.user_id}' not found in system"
            )
        
        # 2. Verify staff_name matches
        if user.username != form_data.staff_name:
            raise HTTPException(
                status_code=400,
                detail=f"Staff name '{form_data.staff_name}' does not match User ID '{form_data.user_id}'"
            )
        
        # 3. Split name into first_name and last_name
        name_parts = form_data.name.strip().split()
        first_name = name_parts[0] if len(name_parts) >= 1 else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # 4. Parse dates
        dob_value = None
        if form_data.birthdate:
            try:
                dob_value = datetime.strptime(form_data.birthdate, "%m/%d/%Y").date()
            except ValueError:
                pass  # Invalid date format, will use age instead

        soc_date_value = None
        if form_data.soc_date:
            try:
                # Try mm/dd/yyyy first, then yyyy-mm-dd
                try:
                    soc_date_value = datetime.strptime(form_data.soc_date, "%m/%d/%Y").date()
                except ValueError:
                    soc_date_value = datetime.strptime(form_data.soc_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        # 5. Build full address
        address_parts = []
        if form_data.address_line1:
            address_parts.append(form_data.address_line1)
        if form_data.address_line2:
            address_parts.append(form_data.address_line2)
        full_address = ", ".join(address_parts) if address_parts else None
        
        # 6. Prepare Lead data
        # Handle age conversion safely (it might be an empty string)
        age_value = None
        if form_data.age and str(form_data.age).strip():
            try:
                age_value = int(form_data.age)
            except ValueError:
                pass

        # Special logic for "Transfer" source
        care_status = None
        active_client = False
        if form_data.source == "Transfer":
            care_status = "Care Start"
            active_client = True
            authorization_received = True
        else:
            authorization_received = False

        lead_data = {
            "staff_name": form_data.staff_name,
            "first_name": first_name,
            "last_name": last_name,
            "source": form_data.source,  # Use dynamic source from form
            "phone": form_data.phone or "",
            "email": form_data.email,
            "city": form_data.city,
            "zip_code": form_data.zip,
            "state": form_data.state,
            "address": full_address,
            "dob": dob_value,
            "age": age_value,
            "soc_date": soc_date_value,
            "care_status": care_status,
            "active_client": active_client,
            "medicaid_status": form_data.medicaid,
            "medicaid_no": form_data.medicaid_number,
            "relation_to_client": form_data.relation,
            "comments": form_data.info,
            "priority": form_data.priority or "Medium",
            "authorization_received": authorization_received,
            "created_by": form_data.staff_name,
        }
        
        # 7. Create lead using CRUD function
        lead_create = LeadCreate(**lead_data)
        # Pass username and user_id for logging
        new_lead = crud_leads.create_lead(
            db, 
            lead_create, 
            username=user.username, 
            user_id=user.id
        )
        
        return {
            "success": True,
            "message": "Lead created successfully",
            "lead_id": new_lead.id,
            "staff_name": new_lead.staff_name,
            "client_name": f"{new_lead.first_name} {new_lead.last_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        db.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Lead Manager API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
