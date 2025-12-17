# Implementation Plan - Lead Manager Setup

## Goal Description
Set up the initial project structure for `lead_manager`, including a virtual environment, SQLAlchemy configuration, and a SQLite database.

## Proposed Changes
### Project Structure
#### [NEW] [db.py](file:///Users/raheelmehar/leads manager/lead_manager/app/db.py)
- Configure SQLAlchemy engine and session.

#### [NEW] [models.py](file:///Users/raheelmehar/leads manager/lead_manager/app/models.py)
- Initial empty models file.

#### [NEW] [create_db.py](file:///Users/raheelmehar/leads manager/lead_manager/create_db.py)
- Script to initialize the database tables.

## Verification Plan
### Automated Tests
- Run `python create_db.py` and check for the existence of `leads.db`.

# Implementation Plan - Phase 2: Models and Schemas

## Goal Description
Implement `User` and `Lead` SQLAlchemy models and corresponding Pydantic schemas. Install `pydantic` dependency.

## Proposed Changes
### Dependencies
- Install `pydantic`.
- Install `passlib[bcrypt]`.

### Models
#### [MODIFY] [models.py](file:///Users/raheelmehar/leads manager/lead_manager/app/models.py)
- Define `User` model with fields: id, username, hashed_password, role, created_at.
- Define `Lead` model with fields: id, created_at, updated_at, staff_name, first_name, last_name, source, active_hh, phone, city, zip_code, dob, medicaid_no, e_contact_name, e_contact_relation, e_contact_phone, last_contact_status, last_contact_date, comments.

### Schemas
#### [NEW] [schemas.py](file:///Users/raheelmehar/leads manager/lead_manager/app/schemas.py)
- Define `UserBase`, `UserCreate`, `UserRead`.
- Define `LeadBase`, `LeadCreate`, `LeadUpdate`, `LeadRead`.

### CRUD
#### [NEW] [crud_users.py](file:///Users/raheelmehar/leads manager/lead_manager/app/crud_users.py)
- Implement password hashing and verification.
- Implement `get_user_by_username`, `create_user`, and `authenticate_user`.

#### [NEW] [crud_leads.py](file:///Users/raheelmehar/leads manager/lead_manager/app/crud_leads.py)
- Implement `create_lead`, `get_lead`, `list_leads`, `update_lead`, and `delete_lead`.

# Implementation Plan - Phase 3: Analytics Services

## Goal Description
Implement statistical analysis services for leads and users.

## Proposed Changes
### Services
#### [NEW] [services_stats.py](file:///Users/raheelmehar/leads manager/lead_manager/app/services_stats.py)
- Implement `get_basic_counts`, `leads_by_staff`, `leads_by_source`, `leads_by_status`, and `monthly_leads`.

## Verification Plan
### Automated Tests
- Create a test script or update `test_backend.py` to verify the statistics functions.

## Verification Plan
### Automated Tests
- Run `python create_db.py` to ensure tables are created without errors.

