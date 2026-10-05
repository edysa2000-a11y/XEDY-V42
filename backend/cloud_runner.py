import sys
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, '.env'))

from backend.telegram.bot import TelegramEcosystem
from backend.telegram.sr_monitor import SRMonitorEngine

WIB = timezone(timedelta(hours=7))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger('xedy.cloud_runner')

ecosystem = TelegramEcosystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('==================================================')
    logger.info('🚀 XEDY CLOUD 24/7 S/R TELEGRAM BOT IS STARTING...')
    logger.info('📍 Timezone: WIB (UTC+7)')
    logger.info('📊 Assets: GOLD (XAUUSD), EURUSD, OIL (WTI), USDJPY')
    logger.info('⏱️ Scheduled Report: Every 15 Minutes (:00, :15, :30, :45)')
    logger.info('⚡ Touch Alerts: Real-time (< 1s)')
    logger.info('💬 Commands: /popup, /sr, /setsnr, /dashboard, /status')
    logger.info('==================================================')
    
    try:
        await ecosystem.start()
        logger.info('✅ Telegram ecosystem successfully started in background.')
    except Exception as e:
        logger.error(f'❌ Failed to start Telegram ecosystem: {e}', exc_info=True)
        try:
            engine = SRMonitorEngine()
            await engine.start()
            logger.info('✅ Fallback SRMonitorEngine started.')
        except Exception as fe:
            logger.error(f'Fallback engine error: {fe}')
            
    yield
    
    logger.info('Shutting down XEDY Cloud Telegram Bot...')
    try:
        await ecosystem.stop()
    except Exception as e:
        logger.error(f'Error during shutdown: {e}')

app = FastAPI(
    title='XEDY 24/7 Cloud Mission Control',
    version='4.2.0',
    lifespan=lifespan
)

@app.get('/')
async def root():
    now_wib = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')
    return {
        'status': 'ONLINE',
        'service': 'XEDY 24/7 Cloud Mission Control Bot',
        'version': '4.2.0',
        'wib_time': now_wib,
        'message': 'Telegram Bot is active 24/7 in the cloud. Local laptop can stay OFF.'
    }

@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run('backend.cloud_runner:app', host='0.0.0.0', port=port)
