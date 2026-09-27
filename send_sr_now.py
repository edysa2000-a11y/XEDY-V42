import sys
import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.telegram.bot import TelegramEcosystem

async def main():
    print("Menginisialisasi Ekosistem Telegram & S/R Monitor Engine...")
    bot_eco = TelegramEcosystem()
    await bot_eco.start()
    
    WIB = timezone(timedelta(hours=7))
    now_wib = datetime.now(WIB)
    
    print("Mengecek harga real-time MT5 & mengirim laporan S/R ke Telegram...")
    await bot_eco.sr_monitor.check_all_symbols(now_wib)
    await bot_eco.sr_monitor.send_hourly_report(now_wib)
    
    print("Laporan S/R Monitor berhasil dikirim ke Telegram!")
    await asyncio.sleep(2)
    await bot_eco.stop()

if __name__ == "__main__":
    asyncio.run(main())
