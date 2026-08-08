@echo off
title XEDY MT5 Cloud Bridge
echo ===================================================
echo   XEDY V37 - MT5 CLOUD BRIDGE CONNECTOR
echo ===================================================
echo Memeriksa instalasi Python dan MetaTrader5...
python -c "import MetaTrader5" 2>NUL
if %errorlevel% neq 0 (
    echo [ERROR] Modul MetaTrader5 tidak ditemukan!
    echo Sedang menginstal modul MetaTrader5 dan python-dotenv...
    pip install MetaTrader5 python-dotenv
)

echo.
echo Pastikan Terminal MetaTrader 5 (MT5) Anda sedang terbuka
echo dan status koneksi broker berwarna hijau!
echo.
pause

echo Menghubungkan ke GitHub Actions Cloud...
python backend\scripts\mt5_cloud_bridge.py
pause
