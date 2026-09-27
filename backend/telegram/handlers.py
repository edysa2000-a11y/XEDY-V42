import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import os

logger = logging.getLogger("xedy.telegram.handlers")

def register_handlers(dp: Dispatcher, admin_id: int, sr_monitor=None):
    """
    Registers all bot commands.
    Secured by comparing user ID with admin_id.
    """
    
    @dp.message(Command("id"))
    async def cmd_id(message: Message):
        await message.answer(f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\nRezim Chat: <b>{message.chat.type.upper()}</b>")

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("✅ XEDY S/R Real-Time Monitor Active.\nKetik /sr untuk melihat status Support & Resistance XAUUSD & USDJPY.")
        
    @dp.message(Command("sr"))
    async def cmd_sr(message: Message):
        if message.from_user.id != admin_id:
            return
        if sr_monitor:
            summary = sr_monitor.get_current_status_summary()
            try:
                from aiogram.types import BufferedInputFile
                photo_bytes = sr_monitor.generate_current_photo_card()
                input_file = BufferedInputFile(photo_bytes, filename="weekly_sr_card.png")
                await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error sending S/R photo on /sr: {e}")
                await message.answer(summary, parse_mode="HTML")
        else:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if message.from_user.id != admin_id:
            return
        sr_info = sr_monitor.get_current_status_summary() if sr_monitor else "S/R Engine: Off"
        await message.answer(f"🤖 <b>STATUS SISTEM XEDY S/R MONITOR</b>\n\n📈 MT5: Terhubung\n⏱️ Interval: 1 Menit\n📍 Timezone: WIB (UTC+7)\n\n{sr_info}", parse_mode="HTML")
        
    @dp.message(Command("pause"))
    async def cmd_pause(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("⏸️ Perintah Jeda Diterima.")
        
    @dp.message(Command("resume"))
    async def cmd_resume(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("▶️ Monitor S/R dilanjutkan.")

    logger.info("Telegram handlers registered.")
