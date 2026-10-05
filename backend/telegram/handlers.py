import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import os

logger = logging.getLogger("xedy.telegram.handlers")

def register_handlers(dp: Dispatcher, admin_id: int, sr_monitor=None):
    """
    Registers all bot commands.
    Secured by comparing chat ID or user ID with admin_id.
    """
    def is_authorized(message: Message) -> bool:
        if not admin_id or admin_id == 0:
            return True
        # Allow if chat is the authorized group/channel or direct from admin
        if message.chat.id == admin_id or message.from_user.id == admin_id:
            return True
        return False
    
    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        await message.answer(
            f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\n"
            f"👤 <b>User ID:</b> <code>{message.from_user.id}</code>\n"
            f"Rezim Chat: <b>{message.chat.type.upper()}</b>"
        )

    @dp.message(Command("start", "help"))
    async def cmd_start(message: Message):
        if not is_authorized(message):
            return
        help_text = (
            "🤖 <b>XEDY MASTER S/R MONITOR BOT ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Memantau 4 Aset Kunci secara Real-Time:\n"
            "• 🟡 <b>GOLD</b> (XAUUSD)\n"
            "• 🔵 <b>EURUSD</b> (EUR/USD)\n"
            "• ⚫ <b>OIL</b> (WTI CRUDE)\n"
            "• 🟣 <b>USDJPY</b> (USD/JPY)\n\n"
            "<b>Perintah Tersedia:</b>\n"
            "/sr — Menampilkan kartu visual S/R 4 pasang terbaru\n"
            "/status — Ringkasan metrik harga & status S/R\n"
            "/id — Mengetahui Chat ID & User ID\n\n"
            "💡 <i>Laporan dikirim otomatis 1 jam sekali, dan notifikasi instan langsung dikirim jika harga mengenai Support / Resistance.</i>"
        )
        await message.answer(help_text, parse_mode="HTML")
        
    @dp.message(Command("sr"))
    async def cmd_sr(message: Message):
        if not is_authorized(message):
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            try:
                photo_bytes = sr_monitor.generate_current_photo_card()
                input_file = BufferedInputFile(photo_bytes, filename="snr_card.png")
                await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error sending S/R photo on /sr: {e}")
                await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if not is_authorized(message):
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    logger.info("Telegram handlers registered successfully.")
