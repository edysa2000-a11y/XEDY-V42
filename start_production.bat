@echo off
title XEDY V41 ULTIMATE - PRODUCTION SERVER
color 0A

echo ========================================================
echo XEDY V41 ULTIMATE
echo Institutional Autonomous AI Trading Platform
echo ========================================================
echo.

:: 1. Menjalankan Sanity Check
echo [1/3] Menjalankan Pemeriksaan Sistem (Sanity Checks)...
"C:\Users\ACER\AppData\Local\Programs\Python\Python314\python.exe" tests\test_sanity.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Sanity check gagal. Membatalkan peluncuran.
    pause
    exit /b %errorlevel%
)
echo.

:: 2. Memastikan Dependencies
echo [2/3] Memastikan semua pustaka terpenuhi (requirements.txt)...
"C:\Users\ACER\AppData\Local\Programs\Python\Python314\python.exe" -m pip install -r requirements.txt --quiet
echo.

:: 3. Meluncurkan Server Produksi
echo [3/3] Meluncurkan XEDY Core di latar belakang (Production Mode)...
echo Tekan CTRL+C kapan saja untuk mematikan sistem darurat.
echo.

:: Menjalankan Uvicorn tanpa --reload untuk performa maksimal
"C:\Users\ACER\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info

pause
