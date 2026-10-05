import sys
import os
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.telegram.bot import TelegramEcosystem
from backend.telegram.sr_monitor import SRMonitorEngine

WIB = timezone(timedelta(hours=7))

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("xedy.sr_local_daemon")

async def main():
    logger.info("==================================================")
    logger.info("🚀 XEDY MASTER S/R REAL-TIME MONITOR DAEMON STARTED")
    logger.info("📍 Timezone: WIB (UTC+7)")
    logger.info("📊 Assets: GOLD (XAUUSD), EURUSD, OIL (WTI), USDJPY")
    logger.info("⏱️ Scheduled Report: Setiap 15 Menit Sekali (:00, :15, :30, :45)")
    logger.info("🚨 Instant Alert: Langsung saat harga mengenai SNR!")
    logger.info("==================================================")
    
    ecosystem = TelegramEcosystem()
    try:
        await ecosystem.start()
    except Exception as e:
        logger.warning(f"TelegramEcosystem polling startup notice: {e}. Starting SRMonitorEngine standalone fallback...")
        engine = SRMonitorEngine()
        await engine.start()
        ecosystem = engine
    
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping local daemon...")
        await ecosystem.stop()

if __name__ == "__main__":
    asyncio.run(main())
