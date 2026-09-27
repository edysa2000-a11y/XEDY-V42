import sys
import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.telegram.sr_monitor import SRMonitorEngine

async def main():
    sr = SRMonitorEngine()
    now_wib = datetime.now(timezone(timedelta(hours=7)))
    
    print("Testing 1. Near Support Alert...")
    await sr.send_instant_alert("XAUUSD", 4240.00, 4220.00, 4580.00, 20.00, 340.00, "NEAR_SUPPORT", now_wib)
    await asyncio.sleep(1)
    
    print("Testing 2. Near Resistance Alert...")
    await sr.send_instant_alert("USDJPY", 158.10, 152.80, 158.30, 5.30, 0.20, "NEAR_RESISTANCE", now_wib)
    await asyncio.sleep(1)
    
    print("Testing 3. Breakout Alert...")
    await sr.send_instant_alert("USDJPY", 158.40, 152.80, 158.30, 5.60, -0.10, "BREAKOUT", now_wib)
    await asyncio.sleep(1)
    
    print("Testing 4. Breakdown Alert...")
    await sr.send_instant_alert("XAUUSD", 4215.00, 4220.00, 4580.00, -5.00, 365.00, "BREAKDOWN", now_wib)
    await asyncio.sleep(1)
    
    print("Testing 5. Hourly Report...")
    await sr.check_all_symbols(now_wib)
    await sr.send_hourly_report(now_wib)
    print("Semua tes alert Telegram berhasil terisi dan teruji!")

if __name__ == "__main__":
    asyncio.run(main())
