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
    logger.info("🚀 XEDY LOCAL S/R REAL-TIME MONITOR DAEMON STARTED")
    logger.info("📍 Timezone: WIB (UTC+7)")
    logger.info("⏱️ Interval: Every 60 seconds (1 minute)")
    logger.info("📊 Hourly Report: Every hour on the hour (:00)")
    logger.info("==================================================")
    
    engine = SRMonitorEngine()
    await engine.start()
    
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping local daemon...")
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
