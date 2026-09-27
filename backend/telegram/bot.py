import asyncio
import logging
from aiogram import Bot, Dispatcher
from .handlers import register_handlers
from .notifier import TelegramNotifier
from .sr_monitor import SRMonitorEngine
import os

logger = logging.getLogger("xedy.telegram.bot")

class TelegramEcosystem:
    """
    Main manager for the Telegram Bot ecosystem.
    Runs completely decoupled from trading logic.
    """
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "DUMMY_TOKEN")
        self.admin_id = int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))
        self.bot = None
        self.dp = None
        self.notifier = None
        self.sr_monitor = SRMonitorEngine()
        self._polling_task = None

    async def start(self):
        if self.token == "DUMMY_TOKEN" or self.admin_id == 0:
            logger.warning("Telegram Bot Token atau Admin ID belum diset. Telegram berjalan dalam mode NONAKTIF.")
            return

        logger.info("Memulai Ekosistem Telegram...")
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        
        # Inisialisasi service
        self.notifier = TelegramNotifier(self.bot, self.admin_id)
        
        # Start AI S/R Monitor Engine
        await self.sr_monitor.start(bot=self.bot, admin_id=self.admin_id)
        
        # Registrasi routing
        register_handlers(self.dp, self.admin_id, sr_monitor=self.sr_monitor)
        
        # Mulai long-polling sebagai background task
        self._polling_task = asyncio.create_task(self._poll())

    async def _poll(self):
        while True:
            try:
                await self.dp.start_polling(self.bot)
            except asyncio.CancelledError:
                logger.info("Telegram polling cancelled.")
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)  # Sleep and retry in case of connection drop

    async def stop(self):
        if hasattr(self, "sr_monitor") and self.sr_monitor:
            await self.sr_monitor.stop()
        if self._polling_task:
            self._polling_task.cancel()
        if self.bot:
            await self.bot.session.close()
            logger.info("Ekosistem Telegram dihentikan.")
