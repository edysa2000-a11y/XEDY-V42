@echo off
title XEDY Backend Server
cd /d "%~dp0"
echo Memulai XEDY Mission Control Backend Server...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
