@echo off
title XEDY V42 - Server Lokal
cls
echo ========================================================
echo   MENJALANKAN SERVER LOKAL XEDY V42...
echo ========================================================
echo.
set PYTHONIOENCODING=utf-8
python backend\scripts\run_local_server.py
if errorlevel 1 (
    echo.
    echo [!] Terjadi kesalahan saat menjalankan Python.
    pause
)
