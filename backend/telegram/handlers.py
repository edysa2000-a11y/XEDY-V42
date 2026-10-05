import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
import os

logger = logging.getLogger("xedy.telegram.handlers")
WIB = timezone(timedelta(hours=7))

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
            f"Rezim Chat: <b>{message.chat.type.upper()}</b>",
            parse_mode="HTML"
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
            "⚡ <b>/popup</b> atau <b>/sr</b> — Request instan Dashboard 16:9 Bloomberg (tanpa tunggu interval)\n"
            "⚙️ <b>/setsnr</b> — Merubah level Support & Resistance lewat Telegram\n"
            "📊 <b>/status</b> — Ringkasan teks metrik harga & status S/R\n"
            "🆔 <b>/id</b> — Mengetahui Chat ID & User ID\n\n"
            "💡 <i>Update otomatis terkirim setiap 15 menit, dan alert visual instan dikirim detik itu juga jika harga mengenai batas SNR.</i>"
        )
        await message.answer(help_text, parse_mode="HTML")
        
    @dp.message(Command("sr", "popup", "dashboard", "now"))
    async def cmd_popup(message: Message):
        """
        Request popup on demand without waiting for scheduled interval.
        Fetches fresh cloud prices and immediately generates the latest 16:9 card.
        """
        if not is_authorized(message):
            return
        if not sr_monitor:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return

        now_wib = datetime.now(WIB)
        try:
            # Rescan live market immediately from cloud
            await sr_monitor.check_all_symbols(now_wib)
            summary = sr_monitor.get_current_status_summary()
            photo_bytes = sr_monitor.generate_current_photo_card()
            input_file = BufferedInputFile(photo_bytes, filename="bloomberg_live.png")
            await message.answer_photo(photo=input_file, caption=summary, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error on on-demand popup: {e}")
            summary = sr_monitor.get_current_status_summary()
            await message.answer(summary, parse_mode="HTML")

    @dp.message(Command("setsnr", "snr", "ubahsnr"))
    async def cmd_setsnr(message: Message):
        """
        Set or update Support & Resistance for any pair directly from Telegram.
        Usage: /setsnr <PAIR> <SUPPORT> <RESISTANCE>
        """
        if not is_authorized(message):
            return
        if not sr_monitor:
            await message.answer("⚠️ S/R Monitor Engine belum diinisialisasi.")
            return

        text = message.text.strip()
        parts = text.split()

        if len(parts) >= 4:
            raw_sym = parts[1]
            try:
                supp = float(parts[2].replace(",", "."))
                res = float(parts[3].replace(",", "."))
            except ValueError:
                await message.answer("⚠️ Format angka tidak valid. Contoh: <code>/setsnr GOLD 3900 4250</code>", parse_mode="HTML")
                return

            success, msg = sr_monitor.set_snr(raw_sym, supp, res)
            if success:
                now_wib = datetime.now(WIB)
                try:
                    await sr_monitor.check_all_symbols(now_wib)
                    summary = sr_monitor.get_current_status_summary()
                    photo_bytes = sr_monitor.generate_current_photo_card()
                    input_file = BufferedInputFile(photo_bytes, filename="snr_updated.png")
                    full_caption = f"{msg}\n\n{summary}"
                    await message.answer_photo(photo=input_file, caption=full_caption, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error rendering after set_snr: {e}")
                    await message.answer(msg, parse_mode="HTML")
            else:
                await message.answer(msg, parse_mode="HTML")
        else:
            # Display current SNR levels and clear instructions
            lines = [
                "⚙️ <b>PENGATURAN LEVEL SUPPORT & RESISTANCE (S/R)</b>",
                "━━━━━━━━━━━━━━━━━━━━━━",
                "<b>Level S/R Aktif Saat Ini:</b>"
            ]
            for sym, cfg in sr_monitor.CONFIG.items():
                digits = cfg["digits"]
                lines.append(f"• <b>{cfg['name']}</b> ({cfg['subtitle']}): S = <code>{cfg['support']:,.{digits}f}</code> | R = <code>{cfg['resistance']:,.{digits}f}</code>")
            
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━",
                "<b>Cara Merubah Level:</b>",
                "Ketik: <code>/setsnr &lt;PAIR&gt; &lt;SUPPORT&gt; &lt;RESISTANCE&gt;</code>\n",
                "<b>Contoh Perintah:</b>",
                "• <code>/setsnr GOLD 3900 4250</code>",
                "• <code>/setsnr USDJPY 156.50 159.80</code>",
                "• <code>/setsnr EURUSD 1.1120 1.1350</code>",
                "• <code>/setsnr OIL 88.00 98.50</code>\n",
                "💡 <i>Setelah diupdate, kartu visual Bloomberg terbaru akan langsung dikirimkan seketika!</i>"
            ])
            await message.answer("\n".join(lines), parse_mode="HTML")

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

