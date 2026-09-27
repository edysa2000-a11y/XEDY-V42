@echo off
title XEDY S/R Real-Time Monitor Daemon (1-Minute Engine)
cd /d "%~dp0"
echo ========================================================
echo   XEDY REAL-TIME S/R 1-MINUTE MONITOR DAEMON
echo   Memantau XAUUSD & USDJPY Setiap 60 Detik
echo   Laporan Per Jam Otomatis ke Telegram
echo ========================================================
python backend/scripts/run_sr_local_daemon.py
pause
