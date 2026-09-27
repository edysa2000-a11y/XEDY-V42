import sys
import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.telegram.sr_monitor import SRMonitorEngine

async def main():
    print("Testing S/R Monitor Visual Photo Card Send...")
    sr = SRMonitorEngine()
    now_wib = datetime.now(timezone(timedelta(hours=7)))
    
    # Populate test data
    sr.last_price_data["XAUUSD"] = {
        "mid": 4285.00,
        "dist_s": 65.00,
        "dist_r": 295.00,
        "status": "NORMAL"
    }
    sr.last_price_data["USDJPY"] = {
        "mid": 157.29,
        "dist_s": 4.49,
        "dist_r": 1.01,
        "status": "NORMAL"
    }
    
    print("Generating & sending S/R Hourly Report with Visual Photo Card...")
    await sr.send_hourly_report(now_wib)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
