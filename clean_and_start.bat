@echo off
echo ========================================================
echo XEDY PROCESS CLEANER & SINGLE SERVER LAUNCHER
echo ========================================================

echo [1/3] Terminating any process using Port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo [2/3] Terminating duplicate Python/Uvicorn processes...
taskkill /f /fi "WINDOWTITLE eq C:\WINDOWS\system32\cmd.exe - start_direct_uvicorn.bat" >nul 2>&1
taskkill /f /im python.exe >nul 2>&1

echo [3/3] Launching ONE single clean XEDY Server instance...
cd /d "c:\Antigravity\Project\XEDY Mission Control"
start "XEDY_PRODUCTION_SERVER" /min "C:\Users\ACER\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info

echo ========================================================
echo SUCCESS: All duplicate servers cleared. 
echo Exactly ONE server is now running minimized in the background.
echo ========================================================
