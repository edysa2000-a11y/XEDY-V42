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
        
        # Registrasi menu tombol resmi Telegram
        try:
            from aiogram.types import BotCommand
            commands = [
                BotCommand(command="menu", description="📱 Menu Dashboard Interaktif"),
                BotCommand(command="rk", description="🎯 Rekomendasi D1 & H4 (/rk <pair>)"),
                BotCommand(command="set", description="🔔 Pasang Reminder (/set USDJPY > 158.2 \"SELL...\")"),
                BotCommand(command="stop", description="🛑 Matikan & Hapus Reminder (/stop USDJPY)"),
                BotCommand(command="reminders", description="📋 Lihat Daftar Reminder Aktif"),
                BotCommand(command="op", description="⚡ Rekomendasi OP USDJPY (Sell 158.20 / TP 157.70)"),
                BotCommand(command="sinyal", description="🎯 Sinyal H1 Qwen Live (OP / TP / SL)"),
                BotCommand(command="history", description="📋 Rekap History OP & Hit TP/SL (05:00 WIB)"),
                BotCommand(command="sr", description="📊 Bloomberg S/R Live Dashboard (16:9)"),
                BotCommand(command="engine", description="🧠 XEDY AI Precision Engine (16:9)"),
                BotCommand(command="flow", description="🌊 Money Flow Radar Dashboard (16:9)"),
                BotCommand(command="nr", description="📜 38 Pertanyaan Inti Kausal (/nr <pair>)"),
                BotCommand(command="setsnr", description="⚙️ Pengaturan Level Support & Resistance"),
                BotCommand(command="legend", description="📖 Panduan Signal Grade & Status"),
                BotCommand(command="status", description="📈 Ringkasan Metrik Pasar"),
            ]
            await self.bot.set_my_commands(commands)
            logger.info("Official Telegram Bot Command Menu registered successfully.")
        except Exception as e:
            logger.warning(f"Could not set bot commands: {e}")
        
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
