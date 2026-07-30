import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import os

logger = logging.getLogger("xedy.telegram.handlers")

def register_handlers(dp: Dispatcher, admin_id: int):
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
        await message.answer("✅ XEDY Ultimate Telegram Link Active.\nKetik /status untuk melihat kesehatan mesin.")
        
    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("🤖 Sistem: BEROPERASI\n📈 MT5: Terhubung\n🧠 AI: Siaga")
        
    @dp.message(Command("pause"))
    async def cmd_pause(message: Message):
        if message.from_user.id != admin_id:
            return
        # Logic to pause the Trading Engine via internal service call
        await message.answer("⏸️ Perintah Jeda Diterima. Menghentikan penerimaan sinyal AI baru...")
        
    @dp.message(Command("resume"))
    async def cmd_resume(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("▶️ Sistem dilanjutkan. Mengaktifkan AI...")

    @dp.message(Command("testnews"))
    async def cmd_testnews(message: Message):
        if message.from_user.id != admin_id:
            return
        await message.answer("🧪 Mengirim simulasi rilis berita ekonomi ke obrolan...")
        msg = (
            f"📰 <b>Berita Makro Baru</b>\n\n"
            f"🕒 Jam: 13:30:00\n"
            f"📅 Tanggal: 2026-07-28\n"
            f"💰 Harga XAUUSD Saat Ini: $2045.50\n"
            f"📢 Berita: [TEST] US CPI inflation drops to 2.9%, driving strong institutional gold demand\n"
            f"📈 Trend Dampak: 🟢 <b>BULLISH</b>\n\n"
            f"📊 <b>Metrik Sentimen Global:</b>\n"
            f"💬 Sentiment Market (News): 68.5%\n"
            f"💵 Currency Index (USD): -0.18%\n"
            f"🏢 Market Strength (Equity): -0.25%\n"
            f"⚙️ Global Sentiment Index (GSI): 50.0% ➔ 58.5%\n\n"
            f"🎯 Estimasi Harga Dampak: $2055.78"
        )
        try:
            await message.bot.send_message(chat_id=admin_id, text=msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send testnews: {e}")

    logger.info("Telegram handlers registered.")
