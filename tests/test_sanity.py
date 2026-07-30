import asyncio
import os
import sys

# Tambahkan path root agar bisa import backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.connection import get_db_connection
import MetaTrader5 as mt5

async def run_sanity_checks():
    print("========================================")
    print("XEDY V41 ULTIMATE - SANITY CHECK")
    print("========================================")
    
    # 1. Check Database
    try:
        conn = await get_db_connection()
        await conn.execute("SELECT 1")
        await conn.close()
        print("[OK] SQLite WAL Database dapat diakses.")
    except Exception as e:
        print(f"[FAIL] Database error: {e}")
        return False
        
    # 2. Check MetaTrader 5
    if not mt5.initialize():
        print(f"[FAIL] MetaTrader5 gagal diinisialisasi. Error code: {mt5.last_error()}")
        print("     -> Pastikan Terminal MT5 sudah terbuka di Windows Anda!")
        return False
        
    print("[OK] MetaTrader 5 Python API terhubung.")
    
    # 3. Check MT5 Account/Terminal info
    terminal_info = mt5.terminal_info()
    if terminal_info is None:
        print("[FAIL] Gagal mendapatkan info Terminal MT5.")
        mt5.shutdown()
        return False
        
    if not terminal_info.trade_allowed:
        print("[WARNING] Terminal MT5 terhubung, TAPI fitur 'AutoTrading' dinonaktifkan di terminal!")
    else:
        print("[OK] AutoTrading (Algo Trading) diizinkan.")
        
    mt5.shutdown()
    
    print("========================================")
    print("SEMUA SISTEM SIAP UNTUK PRODUKSI!")
    print("========================================")
    return True

if __name__ == "__main__":
    success = asyncio.run(run_sanity_checks())
    sys.exit(0 if success else 1)
