import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

from backend.telegram.sr_monitor import SRMonitorEngine

WIB = timezone(timedelta(hours=7))

async def main():
    print("XEDY GitHub 15-Minute Bloomberg SR Push starting...")
    now_wib = datetime.now(WIB)
    engine = SRMonitorEngine()
    print(f"Scanning market symbols at {now_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}...")
    await engine.check_all_symbols(now_wib)
    print("Generating and sending 16:9 Bloomberg dashboard card to Telegram...")
    await engine.send_scheduled_report(now_wib)
    
    # If minute is :00 or :30, also push the Money Flow Radar and XEDY AI Precision Engine
    if now_wib.minute in [0, 30] or (len(sys.argv) > 1 and sys.argv[1] in ["--flow", "--all"]):
        print("Generating and sending 30-Minute Money Flow Radar to Telegram...")
        from backend.telegram.money_flow_engine import MoneyFlowRadarEngine
        flow_engine = MoneyFlowRadarEngine()
        await flow_engine.send_scheduled_radar(now_wib)
        
    if now_wib.minute in [0, 30] or (len(sys.argv) > 1 and sys.argv[1] in ["--engine", "--all"]):
        print("Generating and sending 30-Minute XEDY AI Precision Trading Engine to Telegram...")
        from backend.telegram.precision_engine import PrecisionTradingEngine
        prec_engine = PrecisionTradingEngine()
        await prec_engine.send_scheduled_engine(now_wib)
        
    print("Finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
