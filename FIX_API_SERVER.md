# Fix for "Error generating report: 404 - Not found"

## Problem
The API server is currently running with the old code and doesn't have the new `/api/reports/referrals/export` endpoint loaded.

## Solution: Restart the API Server

### Step 1: Stop the Current API Server

Find the terminal/command prompt where the API server is running and press:
```
Ctrl + C
```

Or if you can't find it, kill the process:
```powershell
# Find the process
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Where-Object {$_.MainWindowTitle -like "*api_server*"}

# Or kill all Python processes on port 8003
netstat -ano | findstr :8003
# Then use the PID to kill it:
taskkill /PID <PID_NUMBER> /F
```

### Step 2: Start the API Server with New Code

```powershell
cd "C:\Users\Nazir Ahmad\Desktop\lead-manager"
python backend/api_server.py
```

### Step 3: Verify the Server Started

You should see:
```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
```

### Step 4: Test the Report

1. Go back to the Streamlit app (refresh if needed)
2. Navigate to "📊 Referral Reports"
3. Click "Generate Referral Report"
4. The download should work now!

## Alternative: Quick Restart Script

Create a file `restart_api.ps1`:
```powershell
# Kill existing API server
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Where-Object {$_.CommandLine -like "*api_server*"} | Stop-Process -Force

# Wait a moment
Start-Sleep -Seconds 2

# Start new API server
cd "C:\Users\Nazir Ahmad\Desktop\lead-manager"
python backend/api_server.py
```

Then run:
```powershell
.\restart_api.ps1
```

## Verification

Once restarted, test the endpoint directly:
```powershell
curl http://localhost:8003/api/reports/referrals/stats
```

Should return:
```json
{"success": true, "statistics": {"sent": 106, "confirmed": 53, "rejected": 0, "total": 159}}
```
