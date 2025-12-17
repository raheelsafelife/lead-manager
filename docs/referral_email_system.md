# Referral Email Reminder System

## Overview
Automatic email reminder system with different schedules based on lead type and referral status.

## Email Schedules

### Interim Referrals
- **Frequency**: Every 6 hours
- **Duration**: 2 days (48 hours total)
- **Total Emails**: Up to 9 emails (at 0h, 6h, 12h, 18h, 24h, 30h, 36h, 42h, 48h)
- **Stops**: After 48 hours OR when status becomes "Inactive"

### Regular Referrals
- **Frequency**: Every 24 hours
- **Duration**: 7 days (168 hours total)
- **Total Emails**: Up to 8 emails (at 0h, 24h, 48h, 72h, 96h, 120h, 144h, 168h)
- **Stops**: After 168 hours OR when status becomes "Inactive"

### Non-Referral Leads
- **Frequency**: Every 48 hours
- **Duration**: Continuous until stopped
- **Total Emails**: Unlimited (continues as long as lead is active)
- **Stops**: When status becomes "Inactive" OR lead becomes a referral

## Email Content

### Regular Lead Emails
Simple template includes:
- Lead name, phone, date of birth
- Source, creator, created date
- Current status

### Referral Emails
Comprehensive template includes:
- **Lead Information**: Name, phone, DOB
- **Referral Details**: 
  - Referral Type (Interim/Regular)
  - Current Status
  - Created By
  - Created Date
- **Payor Information**: 
  - Payor Name
  - Payor Suboption (if applicable)
- **CCU Information**:
  - CCU Name
  - CCU Email
  - Supervisor/Care Coordinator Name

## Implementation Details

### Files Modified
1. **app/utils/email_service.py**
   - Added `send_referral_reminder_email()` function
   - Takes referral_info dict with 12 fields
   - HTML email with color-coded sections

2. **app/email_scheduler.py**
   - Updated `should_send_reminder()` with referral type logic
   - Modified `send_lead_reminders()` to check referral status
   - Uses `send_referral_reminder_email()` for referrals
   - Uses `send_simple_lead_email()` for regular leads

3. **streamlit_app.py**
   - Updated lead creation auto-email (lines 1956-2045)
   - Checks if lead is referral and uses appropriate email template
   - Added crud_ccus to imports
   - Updated admin sidebar to show all three schedules

### Background Scheduler
- Runs as daemon thread on app startup
- Checks every 1 hour for leads needing reminders
- Calculates time since last reminder and time since creation
- Applies different intervals based on referral type
- Records all email attempts in `email_reminders` table

### Database Records
All emails are tracked in the `email_reminders` table:
- `lead_id`: Which lead the email is about
- `recipient_email`: Who received the email
- `subject`: Email subject line
- `sent_at`: Timestamp of sending
- `sent_by`: "system" for automatic, username for manual
- `status`: "sent" or "failed"
- `error_message`: Error details if failed

## Testing Checklist

### Test Interim Referral
1. Create a new lead with:
   - `active_client = True`
   - `referral_type = "Interim"`
   - Payor and CCU assigned
2. Verify first email sent immediately
3. Wait 6 hours, verify second email
4. Check email contains all referral fields
5. Verify emails stop after 48 hours

### Test Regular Referral
1. Create a new lead with:
   - `active_client = True`
   - `referral_type = "Regular"`
   - Payor and CCU assigned
2. Verify first email sent immediately
3. Wait 24 hours, verify second email
4. Check email contains all referral fields
5. Verify emails stop after 168 hours

### Test Non-Referral Lead
1. Create a new lead with:
   - `active_client = False`
2. Verify first email sent immediately
3. Wait 48 hours, verify second email
4. Verify emails continue every 48 hours
5. Set status to "Inactive", verify emails stop

### Test Stop Conditions
1. Create referral, wait for 1-2 reminders
2. Change status to "Inactive"
3. Verify no more emails sent
4. Check admin sidebar shows "✅ Auto-Email Active"

## Admin Dashboard

Admin users see scheduler status in sidebar:
```
✅ Auto-Email Active
📧 Schedules:
• Interim: 6h × 2 days
• Regular: 24h × 7 days
• Leads: 48h until inactive
```

## Manual Email Reminders

Manual "Send Reminder" buttons remain available:
- Use comprehensive `send_lead_reminder_email()` template
- Include ALL lead details (emergency contacts, insurance, etc.)
- Not affected by automatic schedule
- Recorded separately in email_reminders table with `sent_by = username`

## Email Server Configuration

Requires `.env` file with:
```
SMTP_HOST=smtp.safelifehomehealth.com
SMTP_PORT=465
SMTP_USER=your_email@domain.com
SMTP_PASSWORD=your_password
```

## Error Handling

All email failures are:
1. Caught silently (don't block lead creation)
2. Recorded in database with status="failed"
3. Logged to console in scheduler
4. Show brief message to user during lead creation

## Future Enhancements

Potential improvements:
- Configurable schedules per user/agency
- Email templates customization UI
- Pause/resume scheduler controls
- Email delivery reports page
- Multiple recipients per reminder
- SMS/text message reminders
