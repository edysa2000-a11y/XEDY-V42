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
    
    # Tolerance window for GitHub Actions cron scheduler delay (+- 7 minutes around :00 and :30)
    m = now_wib.minute
    is_30m_slot = (m in range(0, 8) or m in range(28, 38) or m >= 58)
    force_all = len(sys.argv) > 1 and sys.argv[1] in ["--all"]
    force_flow = len(sys.argv) > 1 and sys.argv[1] in ["--flow", "--all"]
    force_engine = len(sys.argv) > 1 and sys.argv[1] in ["--engine", "--all"]

    if is_30m_slot or force_flow:
        print("Generating and sending 30-Minute Money Flow Radar to Telegram...")
        from backend.telegram.money_flow_engine import MoneyFlowRadarEngine
        flow_engine = MoneyFlowRadarEngine()
        await flow_engine.send_scheduled_radar(now_wib)
        
    if is_30m_slot or force_engine:
        print("Generating and sending 30-Minute XEDY AI Precision Trading Engine to Telegram...")
        from backend.telegram.precision_engine import PrecisionTradingEngine
        prec_engine = PrecisionTradingEngine()
        await prec_engine.send_scheduled_engine(now_wib)
        
    print("Finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
