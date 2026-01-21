from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


# -------- User Schemas --------

class UserBase(BaseModel):
    username: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    role: str = "user"
    user_id: Optional[str] = Field(None, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Schema for updating user credentials. All fields optional."""
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6)


class UserRead(UserBase):
    id: int
    user_id: Optional[str]
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True  # for Pydantic v2; use orm_mode=True in v1


# -------- Agency Schemas --------

class AgencyBase(BaseModel):
    name: str = Field(..., max_length=150)

class AgencyCreate(AgencyBase):
    pass

class AgencyRead(AgencyBase):
    id: int
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


# -------- Event Schemas --------

class EventBase(BaseModel):
    event_name: str = Field(..., max_length=150)

class EventCreate(EventBase):
    pass

class EventRead(EventBase):
    id: int
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


# -------- Lead Schemas --------

class LeadBase(BaseModel):
    staff_name: str
    first_name: str
    last_name: str
    source: str
    event_name: Optional[str] = None
    word_of_mouth_type: Optional[str] = None
    other_source_type: Optional[str] = None
    active_client: bool = False
    referral_type: Optional[str] = None  # "Regular" or "Interim"
    agency_id: Optional[int] = None
    agency_suboption_id: Optional[int] = None
    ccu_id: Optional[int] = None
    mco_id: Optional[int] = None
    authorization_received: bool = False
    care_status: Optional[str] = None  # "Care Start" or "Not Start"
    priority: Optional[str] = "Medium"  # "High", "Medium", "Low"
    soc_date: Optional[date] = None  # Start of Care date
    phone: str
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    dob: Optional[date] = None
    age: Optional[int] = None
    medicaid_no: Optional[str] = None
    e_contact_name: Optional[str] = None
    e_contact_relation: Optional[str] = None
    e_contact_phone: Optional[str] = None
    last_contact_status: str = "Initial Call"
    last_contact_date: Optional[datetime] = None
    comments: Optional[str] = None
    # New fields
    ssn: Optional[str] = None
    email: Optional[str] = None
    custom_user_id: Optional[str] = None
    owner_id: Optional[int] = None


class LeadCreate(LeadBase):
    """Fields required when creating a lead."""
    pass


class LeadUpdate(BaseModel):
    """All fields optional for partial update."""
    staff_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    source: Optional[str] = None
    event_name: Optional[str] = None
    word_of_mouth_type: Optional[str] = None
    other_source_type: Optional[str] = None
    active_client: Optional[bool] = None
    referral_type: Optional[str] = None
    agency_id: Optional[int] = None
    agency_suboption_id: Optional[int] = None
    ccu_id: Optional[int] = None
    mco_id: Optional[int] = None
    authorization_received: Optional[bool] = None
    care_status: Optional[str] = None
    priority: Optional[str] = None
    soc_date: Optional[date] = None
    phone: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    dob: Optional[date] = None
    age: Optional[int] = None
    medicaid_no: Optional[str] = None
    e_contact_name: Optional[str] = None
    e_contact_relation: Optional[str] = None
    e_contact_phone: Optional[str] = None
    last_contact_status: Optional[str] = None
    last_contact_date: Optional[datetime] = None
    comments: Optional[str] = None
    ssn: Optional[str] = None
    email: Optional[str] = None
    custom_user_id: Optional[str] = None
    owner_id: Optional[int] = None


class LeadRead(LeadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    agency: Optional[AgencyRead] = None

    class Config:
        from_attributes = True  # for Pydantic v2; use orm_mode=True in v1
