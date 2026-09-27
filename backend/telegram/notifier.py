import logging
from aiogram import Bot

logger = logging.getLogger("xedy.telegram.notifier")

class TelegramNotifier:
    """
    Service layer for internal backend engines to push notifications 
    to the Telegram Admin.
    """
    def __init__(self, bot: Bot, admin_id: int):
        self.bot = bot
        self.admin_id = admin_id

    async def notify_trade(self, action: str, symbol: str, price: float, ticket: str):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass
        
    async def notify_news(self, *args, **kwargs):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass

    async def notify_ascii_dashboard(self, ascii_text: str):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass

    async def notify_final_outlook(self, narrative_markdown: str):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass

    async def notify_risk_alert(self, message: str):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass

    async def notify_system_status(self, message: str):
        # Muted: Telegram is reserved exclusively for AI S/R Monitor (XAUUSD & USDJPY)
        pass

    async def _send_safe(self, text: str):
        try:
            if self.bot and self.admin_id:
                await self.bot.send_message(chat_id=self.admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
