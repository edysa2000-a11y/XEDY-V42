@echo off
title XEDY V42 - Local Web Server
cls
echo ========================================================
echo   STARTING XEDY V42 LOCAL SERVER...
echo ========================================================
echo.
set PYTHONIOENCODING=utf-8
python backend\scripts\run_local_server.py
if errorlevel 1 (
    echo.
    echo [!] An error occurred while starting Python.
    pause
)
