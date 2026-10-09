import asyncio
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.scripts.send_d1h4_telegram import send_d1h4_recommendations

WIB = timezone(timedelta(hours=7))

# Jadwal Eksekusi Harian (Jam, Menit) dalam WIB
# 1. 06:00 WIB -> Sesi Subuh / Awal Lilin D1
# 2. 13:30 WIB -> Sesi London Open (Waktu Emas Eksekusi H4 ⭐)
# 3. 20:00 WIB -> Sesi New York Open & Peak Liquidity
TARGET_TIMES = [
    (6, 0),
    (13, 30),
    (20, 0)
]

async def scheduler_loop():
    print(f"[{datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}] XEDY D1 & H4 Cron Scheduler Daemon Started.")
    print("Jadwal Pengiriman Otomatis ke Telegram:")
    for h, m in TARGET_TIMES:
        print(f"  • Pukul {h:02d}:{m:02d} WIB")

    last_dispatched = None

    while True:
        now_wib = datetime.now(WIB)
        current_hour = now_wib.hour
        current_minute = now_wib.minute
        current_date_str = now_wib.strftime("%Y-%m-%d")

        # Cek apakah waktu saat ini cocok dengan salah satu jadwal target
        for h, m in TARGET_TIMES:
            if current_hour == h and current_minute == m:
                dispatch_key = f"{current_date_str}_{h:02d}:{m:02d}"
                if last_dispatched != dispatch_key:
                    last_dispatched = dispatch_key
                    print(f"[{now_wib.strftime('%H:%M:%S WIB')}] CRON TRIGGERED: Mengirim Rekomendasi D1 & H4 ke Telegram...")
                    try:
                        success = await send_d1h4_recommendations()
                        if success:
                            print(f"[{now_wib.strftime('%H:%M:%S WIB')}] SUCCESS: Laporan berhasil dikirim!")
                        else:
                            print(f"[{now_wib.strftime('%H:%M:%S WIB')}] WARNING: Pengiriman gagal.")
                    except Exception as e:
                        print(f"[{now_wib.strftime('%H:%M:%S WIB')}] ERROR: {e}")
                    
                    # Tidur 60 detik agar tidak trigger berulang di menit yang sama
                    await asyncio.sleep(65)
                    break

        await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        print("Scheduler stopped by user.")
