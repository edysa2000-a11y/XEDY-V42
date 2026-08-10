@echo off
title XEDY Mission Control V42 - Server
echo ===================================================
echo Memulai Mesin XEDY Mission Control V42...
echo ===================================================
echo.
echo Menjalankan 5 Aset Risk Engine...
echo Menyambungkan ke MetaTrader 5...
echo Mengaktifkan Dashboard Web di http://localhost:8000
echo.
echo JANGAN TUTUP JENDELA INI SELAMA BOT BERJALAN!
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
