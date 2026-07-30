@echo off
cd /d "c:\Antigravity\Project\XEDY Mission Control"
"C:\Users\ACER\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info
pause
